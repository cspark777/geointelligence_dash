import dash
from dash.dependencies import Output, Input
import dash_core_components as dcc
import dash_html_components as html
import plotly
import random
import plotly.graph_objects as go
from collections import deque

from datetime import datetime, timedelta

time_now = datetime.utcnow().strftime('%H:%M:%S')
X = deque(maxlen=20)
X.append(time_now)
Y = deque(maxlen=20)
Y.append(1)

fig = go.Figure()

fig.add_trace(go.Scatter(x=list(X), y=list(Y), mode='lines', name='Positive'))
fig.update_layout(
    xaxis = dict(
        tickmode = 'array',
        tickvals = list(X),
        ticktext = list(X)
    )
)

app = dash.Dash(__name__)
app.layout = html.Div(
    [
        dcc.Graph(id='live-graph', animate=True, figure=fig),
        dcc.Interval(
            id='graph-update',
            interval=3*1000
        ),
    ]
)

@app.callback(Output('live-graph', 'figure'),
              [Input('graph-update', 'n_intervals')])
def update_graph_scatter(input_data):
    time_now = datetime.utcnow().strftime('%H:%M:%S')
    X.append(time_now)
    Y.append(Y[-1]+Y[-1]*random.uniform(-0.1,0.1))

    print(list(X))
    data = plotly.graph_objs.Scatter(
            x=list(X),
            y=list(Y),
            name='Scatter',
            mode= 'lines+markers'
            )

    return {'data': [data],'layout' : go.Layout(
                xaxis = dict(
                    tickmode = 'array',
                    tickvals = list(X),
                    ticktext = list(X)
                ),
                yaxis=dict(range=[min(Y),max(Y)]),
                transition={
                    'duration': 500,
                    'easing': 'cubic-in-out'
                }
            )}
    


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8052 ,debug=True)