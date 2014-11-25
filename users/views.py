from django.shortcuts import render, render_to_response, RequestContext
from requests_oauthlib import OAuth1
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from users.models import Chat_user
from  main.twitter_data import CONSUMER_KEY, CONSUMER_SECRET
import json
import requests
import oauth2 as oauth
import urlparse


# CONSUMER_KEY and CONSUMER_SECRET are generated by me for an app
# It is saved in main/twitter_data.py and imported here
#
consumer = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
client = oauth.Client(consumer)
client.add_certificate

request_token_url = 'https://api.twitter.com/oauth/request_token'
authorize_url = 'https://api.twitter.com/oauth/authorize'
callback_url = 'https://127.0.0.1:8000/home'

# Implementation of 3-legged twitter authorization
#
def sign_in_by_twitter(request):
    # Obtaining a request token
    #
    oauth_request = oauth.Request.from_consumer_and_token(
            consumer, \
            http_url=request_token_url, \
            parameters = {'oauth_callback':callback_url})
    oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)
    response = requests.get(request_token_url, headers=oauth_request.to_header(), verify=True)
    request_token = dict(urlparse.parse_qsl(response.content))

    # Saving request_token in session
    #
    request.session['auth'] = request_token

    # Redirect to twitter authorization page
    # Get will containt new oauth_token & oauth_verifier
    #
    url = 'https://api.twitter.com/oauth/authorize?oauth_token=%s' % request_token['oauth_token']
    return HttpResponseRedirect(url)

def login_user(request):
    return sign_in_by_twitter(request)


# Last step of log in by twitter
# Converting the request token to an access token
#
def request_token_to_access(oauth_token, oauth_verifier, access_token):
    access_token_url = 'https://api.twitter.com/oauth/access_token?oauth_verifier=' + oauth_verifier

    token = oauth.Token(oauth_token, access_token['oauth_token_secret'])
    oauth_request = oauth.Request.from_consumer_and_token(consumer, http_url=access_token_url)
    oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, token)

    response = requests.post(access_token_url, headers=oauth_request.to_header())
    access_token = dict(urlparse.parse_qsl(response.content))
    return access_token

def user_exists(screen_name):
    chat_users =  Chat_user.objects.all()
    print chat_users
    for x in chat_users:
        print x


def home(request):

    # If login by twitter was not performed go back to login page
    #
    if 'auth' not in request.session: 
        return HttpResponseRedirect("login")

    access_token = request.session['auth']

    # Getting oauth_token & oauth_verifier from request
    #
    oauth_token = request.GET.get("oauth_token", "") 
    oauth_verifier = request.GET.get("oauth_verifier","") 

    # Url to check if proper logging was performed
    # 
    url = 'https://api.twitter.com/1.1/account/verify_credentials.json'

    # Getting the access_token which is responsible for user authentication
    # And saving it in session
    #
    access_token = request_token_to_access(oauth_token, oauth_verifier, access_token)
    request.session['token'] = access_token

    # If login by twitter was not performed go back to login page
    #
    if 'oauth_token' not in access_token:
        return HttpResponseRedirect("login")

    token = oauth.Token(access_token['oauth_token'], access_token['oauth_token_secret'])
    oauth_request = oauth.Request.from_consumer_and_token(consumer, http_url=url)
    oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, token)

    response = requests.get(url, headers=oauth_request.to_header())
    if response.status_code != 200:
      raise Exception("Twitter api did not authenticated correctly")

    # Getting screen_name and friends list
    #
    screen_name = json.loads(response.content)['screen_name']
    user_exists(screen_name)
    #users = get_users_dict(screen_name)

    # For testing if twitter api requests are more then 100
    #
    #users = { '1' : 'Piorek', '2' : 'Tomek', '3' : 'ktos' }
    return render_to_response("home.html",
                                locals(),
                                context_instance=RequestContext(request))

def invalidLogin(request):
    return render_to_response("invalidLogin.html",
			        locals(),
			        context_instance=RequestContext(request))
@login_required
def logout_user(request):
    logout(request)
    return HttpResponseRedirect("home")
