import re, difflib, pickle, time
import easygui as e
import mw_api_client as mw
import mwparserfromhell as mwp

with open('login.txt', 'r') as logininfo:
    en = mw.Wiki(logininfo.readline().strip())
    en_name = logininfo.readline().strip()
    en_pass = logininfo.readline().strip()
    tw = mw.Wiki(logininfo.readline().strip(), 'what is wrong with my user agent jeez')
    tw_name = logininfo.readline().strip()
    tw_pass = logininfo.readline().strip()

#login to enwiki manually since enwiki is on an old mw version
en_tok = en.post_request(action='login',
                         lgname=en_name)['login']['token']
en.post_request(action='login', lgname=en_name,
                lgpassword=en_pass, lgtoken=en_tok)
tw.login(tw_name, tw_pass)

en_ap = en.allpages(namespace=0, limit=300)

try:
    with open('config/seenap.pickle', 'rb') as f:
        seen = pickle.load(f)
except IOError:
    seen = []

en_ap = en.allpages(namespace=0, limit=300, apfrom=seen[-1])

try:
    with open('config/index.pickle', 'rb') as f:
        index = pickle.load(f)
except IOError:
    index = {}

def index_trans(cur, title, content):
    idx = {}
    content = mwp.parse(content)
    idx[title] = {}
    for param in content.filter_templates()[0].params:
        idx[title][str(param.name)] = str(param.value)
    cur.update(idx)

cont = False

try:
    for en_p in en_ap:
        if en_p.title in seen:
            print('\nAlready seen {}, skipping'.format(en_p.title))
            continue
        seen.append(en_p.title)
        tw_p = tw.page(('' if ':' in en_p.title else 'Eng:') + en_p.title)
        print('\nPage {}'.format(tw_p.title))
        en_content = en_p.read()
        try:
            tw_content = tw_p.read()
        except mw.requests.exceptions.ConnectionError as e:
            print(' Disconnected?', e)
            continue
        except mw.NotFound:
            print(' Test Wiki page {} not found, creating...'.format(tw_p.title))
            en_mod_content = mwp.parse(en_content, 0, True)
            for link in en_mod_content.ifilter_wikilinks():
                if link.title.startswith('#') or ':' in link.title:
                    continue
                if link.text is None:
                    link.text = str(link.title)
                link.title = 'Eng:' + str(link.title)
            for template in en_mod_content.ifilter_templates():
                if template.name == 'April Fools':
                    en_mod_content.remove(template)
            en_mod_content = str(en_mod_content).strip()
            if not re.search('^#REDIRECT', en_mod_content, re.I):
                en_mod_content = '{{/translate}}' + en_mod_content
            print('Creation',
                  tw_p.edit(en_mod_content.strip(),
                            'Automated edit: Created Test Wiki copy \
of English Wiki page.')['edit']['result'])
            if not re.search('^#REDIRECT', en_mod_content, re.I):
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
        tw_mod_content = mwp.parse(tw_content, 0, True)
        for link in tw_mod_content.ifilter_wikilinks():
            if link.title.startswith('Eng:'):
                if link.title[4:] == link.text:
                    link.text = None
                link.title = link.title[4:]
        for template in tw_mod_content.ifilter_templates():
            if template.name.endswith('/translate'):
                tw_mod_content.remove(template)
        diff = '\n'.join(difflib.unified_diff(tw_mod_content.splitlines(), en_content.splitlines(), en_p.title, tw_p.title))
        if en_content.strip() != tw_mod_content.strip():
            resp = e.codebox('Confirm that an edit is needed:', 'Confirm edit on {}'.format(tw_p.title), diff)
            if resp is not None:
                resp = resp.strip() or None
            if resp is not None:
                en_mod_content = mwp.parse(en_content, 0, True)
                for link in en_mod_content.ifilter_wikilinks():
                    if link.title.startswith('#') or ':' in link.title:
                        continue
                    if link.text is None:
                        link.text = str(link.title)
                    link.title = 'Eng:' + str(link.title)
                tw_par_content = mwp.parse(tw_content, 0, True)
                for template in tw_par_content.ifilter_templates():
                    if template.name.endswith('/translate'):
                        en_mod_content.insert(0, template)
                    if template.name == 'April Fools':
                        en_mod_content.remove(template)
                print('Edit',
                      tw_p.edit(str(en_mod_content).strip(),
                                'Automated edit: Updated Test Wiki copy \
of English Wiki page.')['edit']['result'])
        else:
            print(' Identical content, skipping')
            continue
        time.sleep(5)
except KeyboardInterrupt:
    if raw_input('Continue on to next section?'):
        cont = True
    else:
        raise
finally:
    with open('config/seenap.pickle', 'wb') as f:
        pickle.dump(seen, f, -1)
    with open('config/index.pickle', 'wb') as f:
        pickle.dump(index, f, -1)

if not cont:
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
