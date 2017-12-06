import re, difflib
import mw_api_client as mw

with open('login.txt', 'r') as logininfo:
    en = mw.Wiki(logininfo.readline().strip())
    en_name = logininfo.readline().strip()
    en_pass = logininfo.readline().strip()
    tw = mw.Wiki(logininfo.readline().strip())
    tw_name = logininfo.readline().strip()
    tw_pass = logininfo.readline().strip()

#login to enwiki manually since enwiki is on an old mw version
en_tok = en.post_request(action='login',
                         lgname=en_name)['login']['token']
en.post_request(action='login', lgname=en_name,
                lgpassword=en_pass, ltoken=en_tok)
tw.login(tw_name, tw_pass)

en_rc = en.allpages(namespace='0', prefix='Eng:() lists block', limit=50)
seen_titles = []
index = {}
def index_trans(cur, title, content):
    idx = {}
    matches = re.findall('\|([a-zA-Z]+)=([^}|\n]+)', content)
    idx[title] = {}
    for ns, name in matches:
        idx[title][ns] = name
    cur.update(idx)

for change in en_rc:
    if change.title not in seen_titles:
        print('\nPage {}'.format(change.title))
        seen_titles.append(change.title)
        try:
            en_content = en.page(change.title).read()
            tw_p = tw.page(('Eng:' if ':' not in change.title else '') + change.title.replace('Scratch Wiki:', 'Test-Scratch-Wiki:'))
            tw_content = tw_p.read()
        except mw.NotFound:
            print(' Missing')
            continue
        #don't count Test wiki artefacts in the comparison
        en_content_c = re.sub(r'{{April Fools}}', '', en_content, 1, re.I)
        tw_content_c = re.sub(r'{{[^}]*/translate}}\n?', '', tw_content, 1)
        tw_content_c = re.sub(r'\[\[Eng:(?P<link>[^|]+)\|(?P=link)\]\]', r'[[\g<link>]]', tw_content_c)
        tw_content_c = re.sub(r'\[\[Eng:', '[[', tw_content_c)
        en_content_c, tw_content_c = en_content_c.strip(), tw_content_c.strip()
        #print a diff
        if en_content_c != tw_content_c:
            print(' Edit')
        #build /translate index
        try:
            tw_trans_cont = tw.page(tw_p.title + '/translate').read()
        except mw.NotFound:
            print(' Missing /translate')
            continue
        print(' Index')
        index_trans(index, tw_p.title + '/translate', tw_trans_cont)

seen_titles = []

for deleted in en.logevents(limit=50, leaction='delete/delete'):
    try:
        if deleted['title'] not in seen_titles:
            seen_titles.append(deleted['title'])
            if deleted['ns'] in (0, 12):
                title = ('Eng:' if ':' not in deleted['title'] else '') + deleted['title']
                print('\nDelete {} and its /translate page'.format(title))
    except KeyError:
        print('\nHidden log')

seen_titles = []

for uploaded in en.logevents(limit=50, letype="upload"):
    if uploaded['title'] not in seen_titles:
        seen_titles.append(uploaded['title'])
        title = ('Eng:' if ':' not in uploaded['title'] else '') + deleted['title']
        print('\n(Re)upload {}'.format(uploaded['title']))

for change in tw.recentchanges(limit=10, rcnamespace=3012,
                               mostrecent=True, rctype='edit'):
    if change.title.endswith('/translate'):
        print('\nIndex {}'.format(change.title))
        index_trans(index, change.title.split('/translate')[0], tw.page(change.title).read())

print('\nIndex:')
print(index)
