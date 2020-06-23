import settings # Import related setting constants from settings.py 
import mysql.connector
import time
import random

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="",
    database="jmzv13_twitter",
    charset = 'utf8'
)

while True:
	time.sleep(10.0)
	cc = random.randint(70, 120)
	print(str(cc))

	sql = "INSERT INTO twitters(id_str, created_at, text, polarity, subjectivity, user_created_at, 	user_location, user_description, user_followers_count, longitude, latitude, retweet_count, favorite_count) VALUES "
	for i in range(cc):
		polarity = random.randint(1, 3) - 2
		sql = sql + "('1268345481144479745', NOW(), 'AAA', " + str(polarity) + ", 1, NOW(), 'NEW YORK', 'Rhett B', 1000, NULL, NULL, 0, 0), "
	sql = sql[:-2]

	#print(sql)
	if mydb.is_connected():
	    mycursor = mydb.cursor()	    
	    mycursor.execute(sql)
	    mydb.commit()
	    mycursor.close()
	