import re, difflib, pickle, time
import easygui as e
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

en_ap = en.allpages(namespace=0, limit=300)

try:
    with open('config/seenap.pickle', 'rb') as f:
        seen = pickle.load(f)
except IOError:
    seen = []

try:
    with open('config/index.pickle', 'rb') as f:
        index = pickle.load(f)
except IOError:
    index = {}

def index_trans(cur, title, content):
    idx = {}
    matches = re.findall('\|([a-zA-Z]+)=([^}|\n]+)', content)
    idx[title] = {}
    for ns, name in matches:
        idx[title][ns] = name
    cur.update(idx)

try:
    for en_p in en_ap:
        if en_p.title in seen:
            print('\nAlready seen {}, skipping'.format(en_p.title))
            continue
        seen.append(en_p.title)
        tw_p = tw.page('Eng:' + en_p.title)
        print('\nPage {}'.format(tw_p.title))
        en_content = en_p.read()
        try:
            tw_content = tw_p.read()
        except mw.NotFound:
            print(' Test Wiki page {} not found, creating...'.format(tw_p.title))
            en_mod_content = re.sub(r'\[\[(?![^|\]]*:)([^\]#][^\]|]+)\]\]',
                                        r'[[Eng:\1|\1]]',
                                        en_content)
            en_mod_content = re.sub(r'\[\[(?![^|\]]*:)([^\]#][^\]|]+)\|([^\]]+)\]\]',
                                    r'[[Eng:\1|\2]]',
                                    en_mod_content)
            if not re.search('^#REDIRECT', en_mod_content, re.I):
                en_mod_content = '{{/translate}}' + en_mod_content
            print('Creation',
                  tw_p.edit(en_mod_content.strip(),
                            'Automated edit: Created Test Wiki copy \
of English Wiki page.')['edit']['result'])
            tran_cont = '{{translate\n' \
                        + '|Eng={0}\n|En={0}'.format(en_p.title) \
                        + '\n}}'
            index_trans(index, tw_p.title, tran_cont)
            print('Creation of Translate Page',
                  tw.page(tw_p.title + '/translate').edit(tran_cont,
                                                          'Automated edit: \
Created translate page for {}.'.format(tw_p.title))['edit']['result'])
            continue
        if not re.search('^#REDIRECT', en_content.strip(), re.I):
            try:
                tran_cont = tw.page(tw_p.title + '/translate').read()
            except mw.NotFound:
                print(' /translate page not found, creating...')
                tran_cont = '{{translate\n' \
                            + '|Eng={0}\n|En={0}'.format(en_p.title) \
                            + '\n}}'
                print('Creation of Translate Page',
                      tw.page(tw_p.title + '/translate').edit(tran_cont,
                                                              'Automated edit: \
Created translate page for {}.'.format(tw_p.title))['edit']['result'])
            print(' Index /translate page')
            index_trans(index, tw_p.title, tran_cont)
        tw_mod_content = re.sub(r'\[\[Eng:([^|\]]+)\]\]', r'[[\1]]', tw_content)
        tw_mod_content = re.sub(r'\[\[Eng:([^|\]]+)\|\1\]\]', r'[[\1]]', tw_mod_content)
        tw_mod_content = re.sub(r'\[\[Eng:([^|\]]+)\|([^|\]]+)\]\]', r'[[\1|\2]]', tw_mod_content)
        tw_mod_content = re.sub(r'{{[^}]*/translate}}\n?', '', tw_mod_content)
        diff = '\n'.join(difflib.unified_diff(tw_mod_content.splitlines(), en_content.splitlines(), en_p.title, tw_p.title))
        if en_content.strip() != tw_mod_content.strip():
            resp = e.codebox('Confirm that an edit is needed:', 'Confirm edit on {}'.format(tw_p.title), diff)
            if resp is not None:
                resp = resp.strip() or None
            if resp is not None:
                en_mod_content = re.sub(r'\[\[(?![^|\]]*:)([^\]#][^\]|]+)\]\]',
                                        r'[[Eng:\1|\1]]',
                                        en_content)
                en_mod_content = re.sub(r'\[\[(?![^|\]]*:)([^\]#][^\]|]+)\|([^\]]+)\]\]',
                                        r'[[Eng:\1|\2]]',
                                        en_mod_content)
                m = re.search('{{[^}]*/translate}}\n?', tw_content)
                if m is not None:
                    en_mod_content = m.group(0) + en_mod_content
                print('Edit',
                      tw_p.edit(en_mod_content.strip(),
                                'Automated edit: Updated Test Wiki copy \
of English Wiki page.')['edit']['result'])
        else:
            print(' Identical content, skipping')
            continue
        time.sleep(5)
finally:
    with open('config/seenap.pickle', 'wb') as f:
        pickle.dump(seen, f, -1)
    with open('config/index.pickle', 'wb') as f:
        pickle.dump(index, f, -1)

raise SystemExit

en_rc = en.allpages(namespace='0', prefix='Eng:() lists block', limit=50)
seen_titles = []
index = {}


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
        en_content_c = en_content
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
