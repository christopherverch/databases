#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import os
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime
UPLOAD_FOLDER = 'static/'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
salt = 'cs3083'
#Initialize the app from Flask
app = Flask(__name__, static_url_path='')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 3306,
                       user='root',
                       password='',
                       db='FlaskDemo',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/photopost', methods=['GET', 'POST'])
def photopost():
    posted=0
    print(request.method)
    user = session['username']
    cursor = conn.cursor();
    query = 'SELECT groupname,owner_username FROM belongto WHERE member_username = %s'
    cursor.execute(query, (user))
    groups=cursor.fetchall()
    for line in groups:
        print(line['groupname']+line['owner_username'])
        
    
    cursor.close()
    if request.method == 'POST':
        
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if not os.path.exists("static/" + user):
                os.makedirs("static/" + user)
            offset=""
            while os.path.isfile("static/" + user + "/" + filename[:-4]+offset+filename[-4:]):
                offset+="_"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], user + "/" + filename[:-4]+offset+filename[-4:]))
            posted=1
            username = session['username']
            cursor = conn.cursor();
            query = 'SELECT MAX(photoid) FROM photo'
            now = datetime.now()
            timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
            cursor.execute(query)
            data = cursor.fetchall()
            newID=data[0]['MAX(photoid)'] + 1
            allFollowers = request.form['allFollowers']
            caption = request.form['caption']
            query = 'INSERT INTO photo (filepath,allFollowers,caption,photoPoster,photoid) VALUES(%s,%s,%s,%s,%s)'
            
            cursor.execute(query, (username + "/" + filename,allFollowers,caption,username,newID))
            conn.commit()
            cursor.close()
            for line in groups:
                print(request.form[(line['groupname']+line['owner_username'])])
                if(request.form[(line['groupname']+line['owner_username'])]=="1"):
                    print("entered")
                    cursor = conn.cursor();
                    query = 'INSERT INTO sharedwith (ownerusername,memberusername,photoid,groupname) VALUES(%s,%s,%s,%s)'
                    cursor.execute(query,(line['owner_username'],username,newID,line['groupname']))
                    conn.commit()
                    cursor.close()
    if(posted==1):
        return render_template('photopost.html', groups = groups, posted = "Photo posted!")
    else:
        return render_template('photopost.html', groups = groups, posted = "")
#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')
@app.route('/viewfollowers', methods=['GET', 'POST'])
def viewfollowers():
    msg=""
    username = session['username']
    cursor = conn.cursor();
    query = 'SELECT username_follower FROM follow WHERE username_followed = %s AND followstatus=1'
    cursor.execute(query, (username))
    followers=cursor.fetchall()
    query = 'SELECT username_follower FROM follow WHERE username_followed = %s AND followstatus=0'
    cursor.execute(query, (username))
    requests=cursor.fetchall()
    if request.method == 'POST':
        msg="successfully updated!"
        for line in requests:
            if(request.form[line['username_follower']]=="0"):
                query = 'DELETE FROM follow WHERE username_followed = %s AND username_follower=%s'
                cursor.execute(query, (username,line['username_follower']))
                print(username+line['username_follower'])
                conn.commit()
            else:
                query = 'UPDATE follow SET followstatus=%s WHERE username_followed = %s AND username_follower = %s'
                cursor.execute(query, (request.form[line['username_follower']],username,line['username_follower']))
                conn.commit()
    query = 'SELECT username_follower FROM follow WHERE username_followed = %s AND followstatus=1'
    cursor.execute(query, (username))
    followers=cursor.fetchall()
    query = 'SELECT username_follower FROM follow WHERE username_followed = %s AND followstatus=0'
    cursor.execute(query, (username))
    requests=cursor.fetchall()
    cursor.close()
    return render_template('viewfollowers.html', followers=followers, requests=requests, msg=msg)
@app.route('/follow', methods=['GET', 'POST'])
def follow():
    msg=""
    if request.method == 'POST':
        msg="error, likely user doesn't exist"
        username = session['username']
        cursor = conn.cursor();
        query = 'SELECT username FROM person WHERE username = %s'
        cursor.execute(query, (username))
        data=cursor.fetchall()
        cursor.execute(query, (request.form['userFollow']))
        data2=cursor.fetchall()
        if(bool(data)):
            if(bool(data2)):
                #checking if both user and who they're trying to follow exist
                query = 'SELECT username_follower FROM follow WHERE username_follower = %s AND username_followed = %s'
                cursor.execute(query, (username,request.form['userFollow']))
                data=cursor.fetchall()
                if(bool(data)):
                    msg="Already requested/accepted."
                else:
                    msg="Sent follow request!"
                    query = 'INSERT INTO follow VALUES (%s,%s,%s)'
                    cursor.execute(query, (username,request.form['userFollow'],0))
                    conn.commit()
        cursor.close()
            
    return render_template('follow.html', msg=msg)

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password'] + salt
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE username = %s and password = %s'
    cursor.execute(query, (username, hashed_password))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        #creates a session for the the user
        #session is a built in
        session['username'] = username
        return redirect(url_for('home'))
    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    fname = request.form['Fname']
    lname = request.form['Lname']
    bio = request.form['bio']
    username = request.form['username']
    password = request.form['password'] + salt
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()


    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE username = %s'
    cursor.execute(query, (username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO person VALUES(%s, %s, %s, %s,%s)'
        cursor.execute(ins, (username, hashed_password,fname,lname,bio))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home')
def home():
    user = session['username']
    return render_template('home.html', username=user)
@app.route('/viewtag', methods=['GET', 'POST'])
def viewtag():
    msg=""
    username = session['username']
    cursor = conn.cursor();
    query = 'SELECT photoid FROM taggedin WHERE username = %s AND tagstatus=0'
    cursor.execute(query, (username))
    unconfirmedtags=cursor.fetchall()
    if request.method == 'POST':
        msg="successfully updated!"
        for line in unconfirmedtags:
            if(str(request.form[str(line['photoid'])])=="0"):
                query = 'DELETE FROM taggedin WHERE username = %s AND photoid= %s'
                cursor.execute(query, (username,line['photoid']))
    
                conn.commit()
            else:
                query = 'UPDATE taggedin SET tagstatus=1 WHERE username = %s AND photoid = %s'
                cursor.execute(query, (username,line['photoid']))
                conn.commit()
                
    query = 'SELECT photoid FROM taggedin WHERE username = %s AND tagstatus=0'
    cursor.execute(query, (username))
    unconfirmedtags=cursor.fetchall()
    return render_template('viewtag.html', unconfirmedtags=unconfirmedtags, msg=msg)

@app.route('/tag', methods=['GET', 'POST'])
def tag():
    
    
    
    
    return render_template('tag.html', photoid=request.form['photoidpost'])
@app.route('/tagprocess', methods=['GET', 'POST'])
def tagProccess():
    
    msg=""
    username = session['username']
    cursor = conn.cursor();
    photoidpost = request.form['photoidpost']
    
    user = request.form['userTag']
    if(user==username):
        #this is someone tagging themselves
        query = 'SELECT Username FROM taggedin WHERE username = %s AND photoid = %s'
        cursor.execute(query, (user,photoidpost))
        data = cursor.fetchall()
        if(bool(data)):
            msg="Already tagged!"
        else:
            msg="tagged you in the photo!"
            query = 'INSERT INTO taggedin VALUES(%s, %s, %s)'
            cursor.execute(query, (user, photoidpost,"1"))
            conn.commit()
        return render_template('tag.html', photoid=photoidpost, msg=msg)
    query = "SELECT username FROM person WHERE username= %s"
    cursor.execute(query, user)
    data = cursor.fetchall()
    if(not bool(data)):
        msg = "User doesn't exist."
    if(bool(data)):
        user2 = [user,user,user,photoidpost]
        query = "select photoid FROM photo NATURAL JOIN person WHERE (( %s IN (select username_follower from follow where username_followed = photoposter AND followStatus = 1) AND allFollowers=1) OR photoid IN (Select photoid from sharedwith as s1 where (memberusername = photoposter AND %s IN (select member_username from belongto as b2 where owner_username=s1.ownerUsername AND b2.groupName = s1.groupName))) OR photoposter = %s) AND photoid=%s GROUP BY photoID ORDER BY postingDate DESC "
        cursor.execute(query, user2)
        data = cursor.fetchall()
        if(not bool(data)):
            msg="User can't see this photo, can't tag this user."
        if(bool(data)):
            query = 'SELECT Username FROM taggedin WHERE username = %s AND photoid = %s'
            cursor.execute(query, (user,photoidpost))
            data = cursor.fetchall()
            if(bool(data)):
                msg="user already tagged! (or requested)"
            else:
                msg="tag request sent!"
                query = 'INSERT INTO taggedin VALUES(%s, %s, %s)'
                cursor.execute(query, (user, photoidpost,"0"))
                conn.commit()
    likes=cursor.fetchall()
    
    cursor.close()
    return render_template('tag.html', photoid=photoidpost, msg=msg)
@app.route('/post', methods=['GET', 'POST'])
def post():
    username = session['username']
    cursor = conn.cursor();
    photoidpost = request.form['photoidpost']
    print(photoidpost)
    cursor = conn.cursor();
    query = "select Username from taggedIn where photoID = %s AND tagStatus = 1"
    cursor.execute(query,photoidpost)
    taggedList=cursor.fetchall()
    query = "select Username,rating from likes where photoID = %s"
    cursor.execute(query,photoidpost)
    likes=cursor.fetchall()
    
    cursor.close()
    print(taggedList)
    return render_template('viewinfo.html', data=photoidpost, tagged=taggedList, likedBy=likes)



@app.route('/show_posts', methods=["GET", "POST"])
def show_posts():
    user = session['username']
    user2 = [user,user,user]
    cursor = conn.cursor();
    query = "select photoid,postingDate,photoposter,filepath,firstName,lastName FROM photo NATURAL JOIN person WHERE ( %s IN (select username_follower from follow where username_followed = photoposter AND followStatus = 1) AND allFollowers=1) OR photoid IN (Select photoid from sharedwith as s1 where (memberusername = photoposter AND %s IN (select member_username from belongto as b2 where owner_username=s1.ownerUsername AND b2.groupName = s1.groupName))) OR photoposter = %s GROUP BY photoID ORDER BY postingDate DESC "
    cursor.execute(query, user2)
    data = cursor.fetchall()
    cursor.close()
    
    return render_template('show_posts.html', poster_name=user, pictures=data)

@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')
        
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
