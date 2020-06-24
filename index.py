import pathlib
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State, ClientsideFunction
import pandas as pd
import plotly_express as px

from datetime import datetime, timedelta

import numpy as np
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate

import random
from collections import deque
from threading import Timer
import time

import mysql.connector
import settings 

from backend import post

mydb = mysql.connector.connect(
    host=settings.MYSQL_HOST,
    user=settings.MYSQL_USER,
    passwd=settings.MYSQL_PASSWORD,
    database=settings.MYSQL_DATABASE,
    charset = 'utf8'
)

app = dash.Dash(__name__,
                external_stylesheets=[
                                      #dbc.themes.BOOTSTRAP,
                                      'assets/css/bootstrap.min.css',
                                      #'https://use.fontawesome.com/releases/v5.11.2/css/all.css',
                                      'assets/css/all.css',
                                      {'href': 'https://fonts.googleapis.com/icon?family=Material+Icons',
                                       'rel': 'stylesheet'},
                                      'assets/css/custom.css' 
                                       ],
                meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"},
                           {'name': 'description', 'content': 'COVID-19 ANALTICAL APP'},
                           {'property': 'og:title', 'content': 'COVID-19 CURVES'},
                           {'property': 'og:type', 'content': 'website'},
                           {'property': 'og:url:', 'content': 'https://covid19-curves.herokuapp.com/'},
                           {'property': 'og:image',
                            'content': 'https://covid19-curves.herokuapp.com/assets/covid-curve-app.png'},
                           {'property': 'og:image:secure_url',
                            'content': 'https://covid19-curves.herokuapp.com/assets/covid-curve-app.png'},
                           {'property': 'og:image:type', 'content': 'image/png'},
                           {'http-equiv': 'X-UA-Compatible', 'content': 'IE=edge'},
                           {'name': "author", 'content': "Alban Tranchard"},
                           {'charset': "UTF-8"},
                           ],

                )

app.title = 'GeoIntelligence'
server = app.server
app.config.suppress_callback_exceptions = True


#config

g_update_interval_time = 10 #10 sec
g_x_axis_count = 30

g_graph1_data = {'x_axis': deque(maxlen=g_x_axis_count), 'y_positive': deque(maxlen=g_x_axis_count), 'y_negative': deque(maxlen=g_x_axis_count), 'y_neutral': deque(maxlen=g_x_axis_count)}

config = {'modeBarButtonsToRemove': ['pan2d', 'select2d', 'lasso2d', 'zoomOut2d', 
                  'zoomIn2d', 'hoverClosestCartesian', 'zoom2d', 
                  'hoverCompareCartesian', 'zoomInGeo', 'zoomOutGeo','hoverClosestGeo', 
                  'hoverClosestGl2d', 'toggleHover', 'zoomInMapbox', 'zoomOutMapbox', 
                  'toggleSpikelines'],
          'displaylogo': False}

# top navbar
navbar_layout = dbc.Navbar(children=[
    html.Div(className="container", children=[
      html.A(
          # Use row and col to control vertical alignment of logo / brand
          dbc.Row([
              dbc.Col(html.Img(src=app.get_asset_url("img/logo.png"), height="96px", style={'stroke': '#508caf'})),    
              dbc.Col(dbc.NavbarBrand("smart", className="ml-2 mr-0",
                                    style={'fontSize': '70px', 'fontWeight': '900', 'color': '#843ccc'})),    
              dbc.Col(dbc.NavbarBrand("analytics", className="",
                                    style={'fontSize': '70px', 'fontWeight': '900', 'color': '#35daf5'})),        
          ], align="center", no_gutters=True),
          href='#'),

      dbc.NavbarToggler(id="navbar-toggler", className="ml-auto"),

      dbc.Collapse(
          dbc.Row([
              dbc.NavLink("Home", href='#'),
              dbc.NavLink("Servicios", href='#services', external_link=True),
              dbc.NavLink("Acerca", href='#about', external_link=True),
              dbc.NavLink("Contacto", href='#contact', external_link=True),
          ], no_gutters=True, className="ml-auto flex-nowrap mt-3 mt-md-0", align="center"),
          id="navbar-collapse", navbar=True),
    ])

], sticky="top", className='mb-4 bg-white', style={'WebkitBoxShadow': '0px 5px 5px 0px rgba(100, 100, 100, 0.1)', })


# add callback for toggling the collapse on small screens
@app.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


# get blog data

if mydb.is_connected():
    mycursor = mydb.cursor()
    sql = "SELECT p.id, su.userid, p.title, p.description, p.image_url, p.created_at FROM post p LEFT JOIN site_user su ON p.userid=su.id ORDER BY p.created_at DESC LIMIT 0, 3"

    mycursor.execute(sql)    
    blogs = mycursor.fetchall()    
    mycursor.close()

blog_divs = []

for (blog_id, blog_userid, blog_title, blog_description, blog_image_url, blog_created_at) in blogs:
    blog = dbc.Row([
        dbc.Col([
            html.H6('Published on : ' + blog_created_at.strftime("%d %b, %Y"), className='blog-createdat'),
            html.A(
                html.H2(blog_title, className='blog-title'), 
                href='/post?id=' + str(blog_id), target='_blank'
            ),            
            html.H6('by ' + blog_userid, className='blog-user'),
        ], className='col-12 col-md-8 col-xl-8 blog-content'),
        dbc.Col([
            html.Img(src=app.get_asset_url(blog_image_url),  style={'width': '100%'})
        ], className='col-12 col-md-4 col-xl-4')        
    ], className='blog-div')
    blog_divs.append(blog)


'''
get graph data
'''

def generate_graph1_data():
    global mydb, g_graph1_data, g_update_interval_time
    
    start = time.time()

    time_now = datetime.utcnow()

    time_interval_before = timedelta(hours=0, minutes=0, seconds=g_update_interval_time)

    time_interval = (time_now - time_interval_before).strftime('%Y-%m-%d %H:%M:%S')
    query = "SELECT polarity, COUNT(polarity) as cc FROM {} WHERE created_at >= '{}' GROUP BY polarity".format(settings.TABLE_NAME, time_interval)

    #print(query)

    graph_data = None
    if mydb.is_connected():
        mycursor = mydb.cursor()        
        mycursor.execute(query)
        graph_data = mycursor.fetchall()   
        mycursor.close()   

    end = time.time()
    elapsed = end - start

    g_graph1_data["x_axis"].append(time_now.strftime('%H:%M:%S'))
    g_graph1_data["y_negative"].append(graph_data[0][1])
    g_graph1_data["y_neutral"].append(graph_data[1][1])
    g_graph1_data["y_positive"].append(graph_data[2][1])

    Timer(g_update_interval_time, generate_graph1_data).start()

generate_graph1_data()


# for line chart
fig = go.Figure()

fig.add_trace(go.Scatter(x=list(g_graph1_data["x_axis"]), y=list(g_graph1_data["y_positive"]), mode='lines', name='Positive'))

fig.add_trace(go.Scatter(x=list(g_graph1_data["x_axis"]), y=list(g_graph1_data["y_neutral"]), mode='lines', name='Neutral'))
fig.add_trace(go.Scatter(x=list(g_graph1_data["x_axis"]), y=list(g_graph1_data["y_negative"]), mode='lines', name='Negative'))

fig.update_layout(  margin={"r": 20, "t": 50, "l": 20, "b": 50}, 
                    width=400,
                    height=400,
                    plot_bgcolor='white',
                    title_text="COVID-19 Twitter Trend", 
                    title_font_size=20,
                    yaxis_title_text="", 
                    title_x=0.05, 
                    yaxis_gridcolor='#eee',  
                    # , title_y=0.95
                    xaxis_title_text='', 
                    showlegend=True, 
                    autosize=False,
                    legend_title="", 
                    legend_font_size=14, 
                    legend=dict(x=.1, y=-.2),
                    legend_orientation="h",
                    xaxis_showspikes=True,
                    xaxis_spikethickness=2, 
                    #yaxis_showspikes=True, 
                    #yaxis_spikethickness=2,
                    #yaxis_tickformat=".0%",
                    ) 


#pie chart
labels = ['Positive', 'Neutral', 'Negative']
values = [g_graph1_data["y_positive"][-1], g_graph1_data["y_neutral"][-1], g_graph1_data["y_negative"][-1]]

fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values)])



blogs_section = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Img(src=app.get_asset_url("img/first_content.jpg"),  style={'stroke': '#508caf', 'width': '100%'})
            ]),
            html.Div(blog_divs, className='blogs-div')
        ], className='col-12 col-md-8 col-xl-8'),
        dbc.Col([
            dcc.Graph(id='live-graph', figure=fig, config=config, animate=True),
            dcc.Graph(id='live-graph_pie', figure=fig_pie, config=config, animate=True),

            dcc.Interval(
                id='graph-update',
                interval=g_update_interval_time * 1000
            ),
        ], className='col-12 col-md-4 col-xl-4')
    ], className=''),
    dbc.Row([], id='services',style={'minHeight': '20vh'}),
], fluid=True, id="blog_section", className="blog-section")

@app.callback([Output('live-graph', 'figure'),Output('live-graph_pie', 'figure')],
              [Input('graph-update', 'n_intervals')])
def update_graph_scatter(input_data):
    global g_graph1_data
    # Create traces    
    
    data0 = go.Scatter(x=list(g_graph1_data["x_axis"]), y=list(g_graph1_data["y_positive"]), mode='lines', name='Positive')
    
    data1 = go.Scatter(x=list(g_graph1_data["x_axis"]), y=list(g_graph1_data["y_neutral"]), mode='lines', name='Neutral')
    data2 = go.Scatter(x=list(g_graph1_data["x_axis"]), y=list(g_graph1_data["y_negative"]), mode='lines', name='Negative')
    
    print("-----")
    print(list(g_graph1_data["x_axis"]))

    min_arr = [min(g_graph1_data["y_negative"]), min(g_graph1_data["y_neutral"]), min(g_graph1_data["y_positive"])]
    max_arr = [max(g_graph1_data["y_negative"]), max(g_graph1_data["y_neutral"]), max(g_graph1_data["y_positive"])]

    layout = go.Layout(  
                    margin={"r": 20, "t": 50, "l": 20, "b": 50}, 
                    width=400,
                    height=400,
                    plot_bgcolor='white',
                    title_text="COVID-19 Twitter Trend", 
                    title_font_size=20,
                    yaxis_title_text="", 
                    title_x=0.05, 
                    yaxis_gridcolor='#eee',  
                    yaxis=dict(range=[0,100]),
                    # , title_y=0.95
                    xaxis_title_text='', 
                    showlegend=True, 
                    autosize=True,
                    legend_title="", 
                    legend_font_size=14, 
                    legend=dict(x=.1, y=-.3),
                    legend_orientation="h",
                    xaxis_showspikes=True,
                    xaxis_spikethickness=2, 
                    xaxis=dict(range=[g_graph1_data["x_axis"][0],g_graph1_data["x_axis"][-1]]),
                    #yaxis_showspikes=True, 
                    #yaxis_spikethickness=2,
                    #yaxis_tickformat=".0%",
                    ) 

    labels = ['Positive', 'Neutral', 'Negative']
    values = [g_graph1_data["y_positive"][-1], g_graph1_data["y_neutral"][-1], g_graph1_data["y_negative"][-1]]

    return {'data': [data0, data1, data2], 'layout' :layout}, {'data': [go.Pie(labels=labels, values=values)]}


work_area_section = dbc.Container([
    dbc.Row([
        html.Span("Nuestras Areas de Trabajo", className='section-title'),
        dbc.Col([
            html.Div([
                html.Div([
                    html.Img(src=app.get_asset_url("img/area1.jpg"))
                ], className="card-img"),
                html.Div([
                    html.H4("INTELIGENCIA DE NEGOCIOS", className="card-title display-2"),
                    html.P("Ayudamos a tu empresa a conocer mejor a tus clientes y a encontrar nuevos clientes", className="card-text display-7")
                ], className="card-box p-5")
            ], className="card-wrap")
        ], className='area-card col-12 col-xl-4'),
        dbc.Col([
            html.Div([
                html.Div([
                    html.Img(src=app.get_asset_url("img/area2.jpg"))
                ], className="card-img"),
                html.Div([
                    html.H4("NTELIGENCIA ELECTORA", className="card-title display-2"),
                    html.P("Te ayudamos a ganar las elecciones y a decidir dónde tienes más oportunidades de ganar", className="card-text display-7")
                ], className="card-box p-5")
            ], className="card-wrap")
        ], className='area-card col-12 col-xl-4'),
        dbc.Col([
            html.Div([
                html.Div([
                    html.Img(src=app.get_asset_url("img/area3.jpg"))
                ], className="card-img"),
                html.Div([
                    html.H4("INTELIGENCIA TERRITORIAL", className="card-title display-2"),
                    html.P("Obtén la máxima ventaja del conocimiento del territorio donde te desempeñas", className="card-text display-7")
                ], className="card-box p-5")
            ], className="card-wrap")
        ], className='area-card col-12 col-xl-4'),

    ], className=''),
    dbc.Row([], id='about',style={'minHeight': '20vh'}),
], fluid=True, id="work_area_section", className="work-area-section")

team_section = dbc.Container([
    dbc.Row([
        html.Span("NUESTRO EQUIPO", className='section-title'),
        dbc.Col([
            html.Div([
                html.Div([
                    html.Img(src=app.get_asset_url("img/member1.jpg"))
                ], className="member-img"),
                html.Div([                    
                    html.P("Vice President", className="member-position"),
                    html.P("ALBERT BUCCHI", className="member-name"),
                    html.P("Lorem Lpsum has been the industry's stbadard dummy text ever slience the 1500s, when an unknwn printer took a gallery of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged.", className="member-desc"),
                    dbc.Row([
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/facebook.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/twitter.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/instagram.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/globe.png"))
                        ], className="col-3")
                    ], className="member-social")
                ], className="member-box")
            ], className="member-wrap")
        ], className='member col-12 col-md-6 col-xl-3'),

        dbc.Col([
            html.Div([
                html.Div([
                    html.Img(src=app.get_asset_url("img/member2.jpg"))
                ], className="member-img"),
                html.Div([                    
                    html.P("CEO", className="member-position"),
                    html.P("STARKEY", className="member-name"),
                    html.P("Lorem Lpsum has been the industry's stbadard dummy text ever slience the 1500s, when an unknwn printer took a gallery of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged.", className="member-desc"),
                    dbc.Row([
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/facebook.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/twitter.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/instagram.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/globe.png"))
                        ], className="col-3")
                    ], className="member-social")
                ], className="member-box")
            ], className="member-wrap")
        ], className='member col-12 col-md-6 col-xl-3'),

        dbc.Col([
            html.Div([
                html.Div([
                    html.Img(src=app.get_asset_url("img/member3.jpg"))
                ], className="member-img"),
                html.Div([                    
                    html.P("ExeTv. Director", className="member-position"),
                    html.P("JOHN DOE", className="member-name"),
                    html.P("Lorem Lpsum has been the industry's stbadard dummy text ever slience the 1500s, when an unknwn printer took a gallery of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged.", className="member-desc"),
                    dbc.Row([
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/facebook.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/twitter.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/instagram.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/globe.png"))
                        ], className="col-3")
                    ], className="member-social")
                ], className="member-box")
            ], className="member-wrap")
        ], className='member col-12 col-md-6 col-xl-3'),

        dbc.Col([
            html.Div([
                html.Div([
                    html.Img(src=app.get_asset_url("img/member4.jpg"))
                ], className="member-img"),
                html.Div([                    
                    html.P("Director", className="member-position"),
                    html.P("ADDY FEUERS TEIN", className="member-name"),
                    html.P("Lorem Lpsum has been the industry's stbadard dummy text ever slience the 1500s, when an unknwn printer took a gallery of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged.", className="member-desc"),
                    dbc.Row([
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/facebook.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/twitter.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/instagram.png"))
                        ], className="col-3"),
                        dbc.Col([
                            html.Img(src=app.get_asset_url("img/globe.png"))
                        ], className="col-3")
                    ], className="member-social")
                ], className="member-box")
            ], className="member-wrap")
        ], className='member col-12 col-md-6 col-xl-3')
        

    ], className=''),
    dbc.Row([], id='contact',style={'minHeight': '20vh'}),
], fluid=True, id="team_section", className="team_-section")

footer_section = dbc.Container([
    dbc.Row([
        html.H4("CopyRight GeoIntelligence")
    ], className='', align="center", style={'height': '150px'}),

], fluid=True, id='footer_section', className='border-top bg-white', style={'borderColor': '#666666'})


index_layout = html.Div(className="container", children=[
    navbar_layout,
    blogs_section,
    work_area_section,
    team_section,
    footer_section
]
)


app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):    
    
    if pathname == '/':
        return index_layout
    elif pathname == '/manage/post':
        return post.layout    
    else:
        return '404'



if __name__ == '__main__':

    app.run_server(debug=True, use_reloader=False, threaded=True, host='127.0.0.1', port=8050)
