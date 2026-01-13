import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from flask_app import app
from auth import register_user

# ensure test user exists
register_user('test', 'pass')

with app.test_client() as c:
    # login first
    resp = c.post('/login', data={'username': 'test', 'password': 'pass'}, follow_redirects=True)
    print('Login status:', resp.status_code)

    # try club search
    resp = c.get('/?q=Arsenal&t=club')
    print('Club search status:', resp.status_code)
    print(resp.get_data(as_text=True)[:1200])

    # try player search
    resp = c.get('/?q=Saka&t=player')
    print('Player search status:', resp.status_code)
    print(resp.get_data(as_text=True)[:1200])
