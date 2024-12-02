from fasthtml.common import *
from fasthtml.oauth import GoogleAppClient, redir_url
from random import choice
from datetime import datetime
import json
import os

if os.getenv('RAILWAY_PROJECT_NAME', None) is not None:
    REDIRECT_SCHEME = 'https'
else:
    REDIRECT_SCHEME = 'http'

SECRET_SESSION_KEY = os.getenv('SECRET_SESSION_KEY', None)

### Database
db = database('data/wordapp.db')

words = db.t.words
if words not in db.t: words.create(id=int, user_id=str, word=str, difficulty=int, display=bool, added_on=str, pk='id') #TODO: ensure words are unique. Make it case insensitive.
Word = words.dataclass()
print('num words:', len(words()))

guesses = db.t.guesses
if guesses not in db.t: guesses.create(id=int, word=str, user_id=str, correct=bool, displayed_at=str, guessed_at=str, pk='id')
Guess = guesses.dataclass()

users = db.t.users
if users not in db.t: users.create(user_id=str, name=str, email=str, user_info=str, last_login=str, pk='user_id')
User = users.dataclass()

### Auth
try:
    _client_id = os.getenv('GOOGLE_CLIENT_ID')
    _client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    if _client_id is None or _client_secret is None:
        raise Exception('GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set')
    oauth_client = GoogleAppClient(client_id=_client_id, client_secret=_client_secret)
except Exception as e:
    print(f"Error: {e}")
    oauth_client = GoogleAppClient.from_file('../client_secret_48335797932-44ckn1tgpps1v9i3faj3u8onjo5blui7.apps.googleusercontent.com.json')

oauth_callback_path = '/auth_redirect'


### App Setup
login_redir = RedirectResponse('/login', status_code=303)

def before(req, session):
    print(f"before called with session: {session}")
    print(f"req.method: {req.method}")
    print(f"req.url: {req.url}")
    print(f"req.headers: {req.headers}")
    print(f"req.query_params: {req.query_params}")
    print(f"req.path_params: {req.path_params}")
    print(f"req.client: {req.client}")
    print(f"req.cookies: {req.cookies}")
    print(f"req.scope: {req.scope}")
    print(f"Route: {req.scope.get('route')}")
    # The `auth` key in the scope is automatically provided to any handler which requests it, and can not
    # be injected by the user using query params, cookies, etc, so it should be secure to use.
    auth = req.scope['auth'] = session.get('user_id', None)
    # If the session key is not there, it redirects to the login page.
    if not auth: return RedirectResponse('/login', status_code=303)
    print(f"auth: {auth}")
    # If the user is not in the database, redirect to the login page.
    if auth not in users: return RedirectResponse('/login', status_code=303)
    print(f"user_id: {auth}")
    # Ensure user can only see their own counts:
    guesses.xtra(user_id=auth)
    users.xtra(user_id=auth)

beforeware = Beforeware(before, skip=['/login', oauth_callback_path, r'/favicon\.ico', r'/static/.*', r'.*\.css', r'/static/images/.*'])

def _not_found(req, exc): return Titled('Oh no!', Div('We could not find that page :('))

app = FastHTML(hdrs=(picolink), exception_handlers={404: _not_found}, before=beforeware, secret_session_key=SECRET_SESSION_KEY)
setup_toasts(app)
rt = app.route

@rt("/{fname:path}.{ext:static}")
def get(fname:str, ext:str): return FileResponse(f'{fname}.{ext}')

@app.get(oauth_callback_path)
def auth_redirect(code: str, request, session, state: str = None):
    print(f"auth_redirect called with session: {session}")
    redir = redir_url(request, oauth_callback_path, scheme=REDIRECT_SCHEME)
    if not code: return "No code provided!"
    print(f"code: {code}")
    print(f"state: {state}") # Not used in this example.
    try:
        user_info = oauth_client.retr_info(code, redir)
        print(f"user_info: {user_info}")
        user_id = user_info[oauth_client.id_key]
        user_email = user_info.get('email', None)
        user_name = user_info.get('name', None)
        print(f"User id: {user_id}")

        token = oauth_client.token["access_token"]

        session['user_id'] = user_id

        # We also add the user in the database, if they are not already there.
        if user_id not in users:
            users.insert(User(user_id=user_id, name=user_name, email=user_email, user_info=json.dumps(user_info), last_login=datetime.now().isoformat()))
        else:
            users.update(dict(user_id=user_id, name=user_name, user_info=json.dumps(user_info), last_login=datetime.now().isoformat()))

        # Redirect to the homepage
        return RedirectResponse('/', status_code=303)

    except Exception as e:
        print(f"Error: {e}")
        return f"Could not log in."


@app.get('/login')
def login(request): 
    redir = redir_url(request,oauth_callback_path, scheme=REDIRECT_SCHEME)
    print(f"redir: {redir}")
    login_link = oauth_client.login_link(redir)
    print(f"login_link: {login_link}")
    return Titled('Login', Article(
        Div(
            Header(H2('Login Options')),
            Hr(),
            A(Img(src='/static/images/signinwithgoogle.png', alt='Google Sign-in'), href=login_link),
            style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;"
        )
    ))


@app.get("/logout")
def logout(session):
    session.pop('user_id', None)
    return login_redir

# @patch
# def __ft__(self:Todo):
#     show = AX(self.title, f'/todos/{self.id}', id_curr)
#     edit = AX('edit',     f'/edit/{self.id}' , id_curr)
#     dt = ' (done)' if self.done else ''
#     return Li(show, dt, ' | ', edit, id=tid(self.id))

def get_word(auth, session):
    words_result = words(where=f"user_id='{auth}' AND display=true")
    if not words_result: return 'No words found. Add some starter words.'
    session.setdefault('word_history', [])
    word = choice(words_result)
    word_display_modification = choice([str.lower, str.upper, str.title])
    word_str = word_display_modification(word.word)
    displayed_at = datetime.now().isoformat()
    session['word_history'] = [word.id] + session['word_history']
    if len(session['word_history']) > 10: session['word_history'] = session['word_history'][:10]
    return Article(
         Div(word_str, style="font-size: clamp(16px, 20vw, 200px); text-align: center; padding: 10px; width: 100%; box-sizing: border-box; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"), 
         Footer(
             Div(
                 Button('👍', hx_post=f'/guess?word={word_str}&correct=correct&displayed_at={displayed_at}', hx_target='#word', hx_swap='outerHTML', style='margin: 0.5rem;', 
                        hx_trigger="click, keyup[key=='y'||key=='c'||key=='ArrowUp'] from:body", data_tooltip="Correct - Press y, c, or the up arrow"),
                 Button('👎', hx_post=f'/guess?word={word_str}&correct=incorrect&displayed_at={displayed_at}', hx_target='#word', hx_swap='outerHTML', style='margin: 0.5rem;', 
                        hx_trigger="click, keyup[key=='n'||key=='x'||key=='i'||key=='ArrowDown'] from:body", data_tooltip="Incorrect - Press n, x, i, or the down arrow"),
                 Button('Next', hx_get='/next_word', hx_target='#word', hx_swap='outerHTML', style='margin: 0.5rem;', 
                        hx_trigger="click, keyup[key==' '||key=='Enter'||key=='ArrowRight'] from:body", data_tooltip="Next - Press space, enter, or the right arrow"),
                 Button('Hide', hx_put=f'/words?id={word.id}&display=false', hx_trigger='click, keyup[key=="h"] from:body', 
                        **{'hx-on::before-request':'htmx.ajax("GET", "/next_word", {target: "#word", swap: "outerHTML"})'}, style='margin: 0.5rem;', data_tooltip="Hide - Press h"),
                #  Button('Hide', **{'hx-on::before-request':f"htmx.ajax('PUT', '/words?id={word.id}&display=false', {{target: 'body', swap: 'none'}}); htmx.ajax('GET', '/next_word', {{target: '#word', swap: 'outerHTML'}});"}, style='margin: 0.5rem;', hx_trigger="click, keyup[key=='h'] from:body", data_tooltip="Hide - Press h"),
                 class_='container text-center'
             ),
             style='display: flex; justify-content: center;'
         ),
         id='word')

@rt("/guess")
def post(auth, session, word: str, correct: str, displayed_at: str = None):
    is_correct = correct == 'correct'
    guesses.insert(Guess(word=word, user_id=auth, correct=is_correct, displayed_at=displayed_at, guessed_at=datetime.now().isoformat()))
    return get_word(auth, session)

@rt("/next_word")
def get(auth, session):
    return get_word(auth, session)

@rt("/data")
def get(auth):
    return Title('Data'), Main(get_nav(auth), H1('Data'),
        Div(f'Auth: {auth}'),
        H2('Users'),
        Table(
            Tr(
                Th(Strong('User ID')),
                Th(Strong('Name')),
                Th(Strong('Email')),
                Th(Strong('User Info')),
                Th(Strong('Last Login'))
            ),
            *[Tr(
                Td(u.user_id),
                Td(u.name),
                Td(u.email),
                Td(u.user_info),
                Td(u.last_login)
            ) for u in users()]
        ),
        H2('Words'),
        Table(
            Tr(
                Th(Strong('ID')),
                Th(Strong('User ID')),
                Th(Strong('Word'))
            ),
            *[Tr(
                Td(w.id),
                Td(w.user_id),
                Td(w.word)
            ) for w in words()]
        ),
        H2('Guesses'),
        Table(
            Tr(
                Th(Strong('ID')),
                Th(Strong('User')),
                Th(Strong('Word')),
                Th(Strong('Result')),
                Th(Strong('Displayed At')),
                Th(Strong('Guessed At'))
            ),
            *[Tr(
                Td(g.id),
                Td(users[g.user_id].name),
                Td(g.word),
                Td('✅' if g.correct else '✗'),
                Td(g.displayed_at),
                Td(g.guessed_at)
            ) for g in guesses()]
        ),
        cls='container'
    )

def get_words_table_row(w: Word, hx_swap_oob: str = None):
    return Tr(
        Td(w.id, hidden=True),
        Td(w.word),
        Td(w.difficulty),
        Td(A('✅' if w.display else '❌', hx_put=f'/words?id={w.id}&display=true' if not w.display else f'/words?id={w.id}&display=false')),
        Td(w.added_on),
        Td(
            # A('Edit', hx_get=f'/words/modal?id={w.id}', hx_target='#words-modal', hx_swap='outerHTML'), 
            A('Delete', hx_delete=f'/words?id={w.id}', hx_target=f'#words-row-{w.id}', hx_swap='delete')),
        id=f"words-row-{w.id}",
        hx_swap_oob=hx_swap_oob
    )

def get_words_table(auth):
    words_result = words(where=f"user_id='{auth}'", order_by='word')
    return Table(
            Tr(
                Th(Strong('Word')),
                Th(Strong('Difficulty')),
                Th(Strong('Displayed')),
                Th(Strong('Added On')),
                Th(Strong('Actions')),
            ),
            *[get_words_table_row(w) for w in words_result],
            id='words-table',
            hx_swap_oob="true"
        )

@rt("/words")
def get(auth):
    return Title('Words'), Main(
        get_nav(auth),
        H2('Words'),
        Button('Add word', hx_get='/words/modal', hx_target='#words-modal', hx_swap='outerHTML'),
        Dialog(id='words-modal'),
        get_words_table(auth),
        cls='container'
    )

@rt("/words/modal")
def get(auth):
    return Dialog(
            Article(
                H2('Add word'),
                Form(
                    Label('Word:', for_='word'),
                    Input(name='word', id='word', placeholder='Word'),
                    Label('Difficulty (1 easy - 5 hard):', for_='difficulty'),
                    Input(name='difficulty', id='difficulty', type='number', min='1', max='5', placeholder='Difficulty'),
                    id='words-modal-form'
                ),
                Footer(
                    Div(
                        Button('Add', type='submit', hx_post='/words', hx_swap='outerHTML', hx_include='#words-modal-form'),
                        Button('Cancel', type='button', onclick='me("#words-modal").attribute("open", null)'),
                        style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px;'
                    )
                ),
                cls='modal-content'
            ),
            id='words-modal',
            open=True
        )

@rt("/words")
def post(auth, session, word: str, difficulty: int):
    word = word.lower()
    assert difficulty in range(1, 6), 'Difficulty must be between 1 and 5'
    existing_words = [w.word for w in words(f"user_id='{auth}' AND word=?", (word,))]
    print('add-word query result:', existing_words)
    if word in existing_words:
        add_toast(session, f"Word '{word}' already exists.", "warning")
        return Dialog(id='words-modal', hx_swap_oob='true')
    words.insert(Word(word=word, user_id=auth, difficulty=difficulty, display=True, added_on=datetime.now().isoformat()))
    add_toast(session, f"Word '{word}' was added.", "success")
    return Dialog(id='words-modal', hx_swap_oob='true'), get_words_table(auth)

@rt("/words")
def delete(auth, id: int, session):
    words.xtra(user_id=auth)
    word = words[id].word
    words.delete(id)
    add_toast(session, f"Word '{word}' was deleted.", "success")
    return None

@rt("/words")
def put(auth, id: int, word: str = None, difficulty: int = None, display: bool = None):
    words.xtra(user_id=auth)
    update_dict = dict(id=id)
    if word is not None: update_dict['word'] = word
    if difficulty is not None: update_dict['difficulty'] = difficulty
    if display is not None: update_dict['display'] = display
    updated_word = words.update(update_dict)
    return get_words_table_row(updated_word, hx_swap_oob='true')

def get_nav(auth):
    user = users[auth]
    return Nav(
        Ul(Li(Strong('Learn to read'))),
        Ul(
        Li(Span(f"{user.name} ({user.email})", cls='secondary')),
        Li(Details(Summary('Navigation'),
                Ul(
                    Li(A('Home', href='/')),
                    Li(A('Words', href='/words')),
                    Li(A('Data', href='/data')),
                    Li(A('Logout', href='/logout')),
                    dir='rtl'
                ),
                cls='dropdown'
            )
        )
    )
)

@rt("/add-starter-words")
def get(auth):
    assert auth is not None and auth in users, 'User not found'
    with open('starter_words.json') as f:
        starter_words = json.load(f)
    words_in_db = [w.word.lower() for w in words(where=f"user_id='{auth}'")]
    for word, data in starter_words.items():
        word = word.lower()
        if word not in words_in_db:
            words.insert(Word(word=word, user_id=auth, difficulty=data['difficulty'], display=True, added_on=datetime.now().isoformat()))
    return 'Starter words added.'

@rt("/")
def get(auth, session):
    return Title('Learn to read'), Main(get_nav(auth), get_word(auth, session), Footer(Button('Add starter words', hx_get='/add-starter-words')), cls='container')

serve()