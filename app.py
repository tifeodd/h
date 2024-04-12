#!/usr/bin/env python3
import sys
from flask import Flask, jsonify, abort, request, make_response, session
from flask_restful import reqparse, Resource, Api
from flask_session import Session
import json
import pymysql
import pymysql.cursors
import ssl  # include ssl libraries
import datetime

import settings  # Our server and db settings, stored in settings.py
from shorten_url import shorten_url

app = Flask(__name__)
# CORS(app)
# Set Server-side session config: Save sessions in the local app directory.
app.config['SECRET_KEY'] = settings.SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_NAME'] = 'peanutButter'
app.config['SESSION_COOKIE_DOMAIN'] = settings.APP_HOST

Session(app)

api = Api(app)
##################################################################################
class Root(Resource):
   # get method. What might others be aptly named? (hint: post)
        def get(self):
                return app.send_static_file('spa.html')


class Developer(Resource):
   # get method. What might others be aptly named? (hint: post)
        def get(self):
                return app.send_static_file('developer.html')
####################################################################################
#
# Database connection
#
def connect_db():
    db_connection = pymysql.connect(
                    host=settings.DB_HOST,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWD,
                    database=settings.DB_DATABASE,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
    return db_connection


####################################################################################
#
# Error handlers
#
@app.errorhandler(400)  # decorators to add to 400 response
def bad_request(error):
    error_message = str(error)
    return make_response(jsonify({'status': 'Bad request'}), 400)


@app.errorhandler(401)  # decorators to add to 401 response
def unauthorized(error):
    error_message = str(error)
    return make_response(jsonify({'status': 'Unauthorized'}), 401)


@app.errorhandler(404)  # decorators to add to 404 response
def not_found(error):
    error_message = str(error)
    return make_response(jsonify({'status': 'Resource not found'}), 404)

@app.errorhandler(409)  # decorators to add to 404 response
def not_found(error):
    error_message = str(error)
    return make_response(jsonify({'status': 'Conflict'}), 409)

@app.errorhandler(500)  # decorators to add to 500 response
def internal_server_error(error):
    error_message = str(error)
    return make_response(jsonify({'status': 'Internal server error'}), 500)


####################################################################################
### Example curl command
### curl -X POST -k https://cs3103.cs.unb.ca:8054/auth/login -H "Content-Type: application/json" -c cookie-jar -d '{"email": "user@example.com", "password": "password123"}'
class AuthLogin(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True)
        parser.add_argument('password', type=str, required=True)
        args = parser.parse_args()

        # Check if the user exists in the database
        try:
            db_connection = connect_db()
            cursor = db_connection.cursor()
            cursor.callproc('checkUserExists', (args['email'],))
            result = cursor.fetchone()
            user_exists = result['UserExists']
        except Exception as e:
            abort(500)
        finally:
            cursor.close()
            db_connection.close()

        if user_exists:
            # Check if the provided password matches the one in the database
            try:
                db_connection = connect_db()
                cursor = db_connection.cursor()
                cursor.execute("SELECT UserID FROM Users WHERE Email = %s AND Password = %s",
                               (args['email'], args['password']))
                user = cursor.fetchone()
                if user:
                    # Set session cookie to indicate successful authentication
                    session['user_id'] = user['UserID']
                    return make_response(jsonify({'message': 'Authentication successful', 'user_id': session['user_id']}, 200))
                else:
                    abort(401, message="Unauthorized")
            except Exception as e:
                abort(500)
            finally:
                cursor.close()
                db_connection.close()
        else:
            try:
                db_connection = connect_db()
                cursor = db_connection.cursor()
                cursor.callproc('addUser', ('email', 'password'))
                result = cursor.fetchone()
    
                user_id = result.get('New User ID') 
                session['user_id'] = user_id
                db_connection.commit()
            except Exception as e:
                abort(500)
            finally:
                cursor.close()
                db_connection.close()
    
            return make_response(jsonify({'userId': user_id}, 200))
            
    # Example curl command:
    # curl -X DELETE -H "Content-Type: application/json" -b cookie-jar -k https://cs3103.cs.unb.ca:8054/auth/login
    def delete(self):
        if 'user_id' in session:
            del session['user_id']
            response = {'status': 'success', 'message': 'Logged out successfully'}
            responseCode = 200
        else:
            response = {'status': 'fail', 'message': 'No active session'}
            responseCode = 403

            return make_response(jsonify(response), responseCode)

class Urls(Resource):
    ### Example curl command
    #  curl -X POST -H "Content-Type: application/json" -d '{"url": "https://example2.com/your/long/url"}' -b cookie-jar -k https://cs3103.cs.unb.ca:8054/urls
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('url', type=str, required=True)
        args = parser.parse_args()

        try:
            db_connection = connect_db()
            cursor = db_connection.cursor()

            # Check if URL exists
            cursor.callproc('checkIfUrlAdded', (args['url'],))
            result = cursor.fetchone()
            url_exists = result['UrlExists']

            if url_exists:
                cursor.callproc('GetURLID', (args['url'], session['user_id']))
                result = cursor.fetchone()
                url_ID = result['URL_ID']
            else:
                # Call addURL with shortened URL
                cursor.callproc('addURL', (shorten_url(args['url']), args['url'], session['user_id'], datetime.datetime.now()))
                result = cursor.fetchone()
                session['shortUrlKey'] = shorten_url(args['url'])
                url_ID = result['New URL ID'] 
                db_connection.commit()

        except Exception as e:
            abort(500)
        finally:
            cursor.close()
            db_connection.close()

        return make_response(jsonify({'URL ID': url_ID}, 200))

    ### Example curl command
    #  curl -X PUT -H "Content-Type: application/json" -d '{"old_url": "https://example2.com/your/long/url","new_url": "https://example.com/new"}' -b cookie-jar -k https://cs3103.cs.unb.ca:8054/urls
    def put(self):
        parser = reqparse.RequestParser()
        parser.add_argument('old_url', type=str, required=True)
        parser.add_argument('new_url', type=str, required=True)
        args = parser.parse_args()

        try: 
            db_connection = connect_db()
            cursor = db_connection.cursor()

            # Check if URL exists
            cursor.callproc('checkIfUrlAdded', (args['new_url'],))
            result = cursor.fetchone()
            url_exists = result['UrlExists']

            if url_exists:
                cursor.callproc('GetURLID', (args['new_url'], session['user_id']))
                result = cursor.fetchone()
                url_ID = result['URL_ID']
                return make_response(jsonify({'Conflict': 'URL already exists in database under this user'}, 409, {'URL ID': url_ID}))
            else:
                # Call updateURL with the new shortened URL
                cursor.callproc('GetURLID', (args['old_url'], session['user_id']))
                result = cursor.fetchone()
                url_ID = result['URL_ID']
                cursor.callproc('updateURL', (shorten_url(args['new_url']), args['new_url'], session['user_id'], datetime.datetime.now(), url_ID))
                result = cursor.fetchone()
                status = result['update_-status'] 
                db_connection.commit()

                if status: #if update was successful
                    return make_response(jsonify({'message': 'URL updated successfully'}, 200))
                else: 
                    return make_response(jsonify({'error': 'URL was not updated successfully'}, 500))
                    
        except Exception as e:
            abort(500)
        finally:
            cursor.close()
            db_connection.close()
        
    ### Example curl command
    # curl -X DELETE -H "Content-Type: application/json" -d '{"url": "https://example.com"}' -b cookie-jar -k https://cs3103.cs.unb.ca:8054/urls
    def delete(self):
        parser = reqparse.RequestParser()
        parser.add_argument('url', type=str, required=True)
        args = parser.parse_args()

        try: 
            # Get URL ID
            db_connection = connect_db()
            cursor = db_connection.cursor()
            cursor.callproc('GetURLID', (args['url'], session['user_id']))
            result = cursor.fetchone()
            url_id = result['URL_ID']
            cursor.close()
            
            if url_id is not None: 
                # Delete URL
                cursor = db_connection.cursor()
                cursor.callproc('deleteURL', (session['user_id'], url_id))
                db_connection.commit()  # Commit the changes
                return make_response(jsonify({'message': 'URL deleted successfully'}, 200))
            else:
                return make_response(jsonify({'error': 'URL not found'}, 404))
                
        except Exception as e:
            abort(500)
        finally:
            cursor.close()
            db_connection.close()

            
class UserUrls(Resource):
    ### Example curl command
    ### curl -X GET -b cookie-jar -k https://cs3103.cs.unb.ca:8054/user/urls
    def get(self):
        # Call stored procedure GetAllURLs
        try:
            db_connection = connect_db()
            cursor = db_connection.cursor()
            cursor.callproc('GetAllURLs', (session['user_id'],))
            result = cursor.fetchall()
            urls = []
            for row in result:
                url = {
                    'ShortURL': row['ShortURL'],
                    'LongURL': row['LongURL'],
                    'CreationDate': row['CreationDate'].strftime('%Y-%m-%d %H:%M:%S')  # Convert datetime to string
                }
                urls.append(url)
        except Exception as e:
            abort(500)
        finally:
            cursor.close()
            db_connection.close()

        return make_response(jsonify({'urls': urls}, 200))

class RedirectUrl(Resource):
    def get(self, short_key):
        try:
            db_connection = connect_db()
            cursor = db_connection.cursor()
            cursor.callproc('GetLongURLfromKey', (short_key))
            result = cursor.fetchone()
            long_url = result['LongURL']
            if long_url:
              return make_response(jsonify({'message': 'Redirecting...'}), 302, {'Location': long_url})
            else:
              abort(404)  # URL not found
        except Exception as e:
            abort(500)
        finally:
            cursor.close()
            db_connection.close()

api.add_resource(Root,'/')
api.add_resource(Developer,'/dev')
api.add_resource(AuthLogin, '/auth/login')
api.add_resource(Urls, '/urls')
api.add_resource(UserUrls, '/user/urls')
api.add_resource(RedirectUrl, '/s/<string:short_key>')

if __name__ == "__main__":
    # Load SSL context with certificates
    context=('cert.pem', 'key.pem')  # Replace 'cert.pem' and 'key.pem' with your certificate files

    # Run the Flask app with SSL
    app.run(
        host=settings.APP_HOST,
        port=settings.APP_PORT,  # Use xxxxx as the port
        ssl_context=context,
        debug=settings.APP_DEBUG
        )
