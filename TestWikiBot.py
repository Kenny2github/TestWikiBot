"""This bot updates Test wiki copies of English wiki pages."""
import re
try:
    import cPickle as pickle #prefer C version
except ImportError:
    import pickle
import time
from random import randint
from difflib import unified_diff
import easygui
import mw_api_client as mwc
import mwparserfromhell as mwp

with open('login.txt', 'r') as logininfo:
    print('Init en')
    en = mwc.Wiki(logininfo.readline().strip())
    en_name = logininfo.readline().strip()
    en_pass = logininfo.readline().strip()
    print('Init tw')
    tw = mwc.Wiki(logininfo.readline().strip(),
                  'Random user-agent string: '
                  + str(randint(500, 5000)))
    tw_name = logininfo.readline().strip()
    tw_pass = logininfo.readline().strip()

#login to enwiki manually since enwiki is on an old mw version
print('Login to en')
print(en.login(en_name, en_pass)['result'])
print('Login to tw')
print(tw.login(tw_name, tw_pass)['result'])

def normalize(contents, to='tw', title=None):
    """Normalize a page's contents to a certain wiki's conventions.
    The ``title`` parameter is for context.
    """
    if to == 'en':
        mod_contents = mwp.parse(contents, 0, True)
        for link in mod_contents.ifilter_wikilinks():
            link.title.lstrip('Eng:')
            if link.title == link.text:
                link.text = None
            if link.title.startswith('Category:'):
                link.title = re.sub('Category:[a-z]{3}/(.*)',
                                    r'Category:\1',
                                    str(link.title),
                                    0, re.I)
        for template in mod_contents.ifilter_templates():
            if template.name.endswith('/translate'):
                mod_contents.remove(template)
        return str(mod_contents)
    mod_contents = mwp.parse(contents, 0, True)
    for link in mod_contents.ifilter_wikilinks():
        if link.title[0] not in ('#', '/') \
           and not re.search('^[a-z]+:', str(link.title), re.I):
            if link.text is None:
                link.text = link.title
            link.title = 'Eng:' + str(link.title)
    for template in mod_contents.ifilter_templates():
        if template.name.lower() == 'april fools':
            mod_contents.remove(template)
    mod_contents = '{{' \
                   + f':Eng:{title}' \
                   + '/translate}}' \
                   + str(mod_contents)
    return str(mod_contents)

try:
    with open('pickles/index.pickle', 'rb') as pick:
        translation_index = pickle.load(pick)
except IOError:
    translation_index = {}

def index(curr: dict, tpage: mwc.Page):
    """Index a /translate page."""
    newidx = {}
    content = mwp.parse(tpage.read())
    title = tpage.title.rstrip('/translate')
    newidx[title] = {}
    for param in content.filter_templates()[0].params:
        newidx[title][str(param.name)] = str(param.value)
    curr.update(newidx)
    with open('pickles/index.pickle', 'wb') as pickl: # always dump after update
        pickle.dump(curr, pickl)

try:
    with open('pickles/startfrom.txt', 'r') as startfrom:
        startfrom = startfrom.read().strip()
except IOError:
    startfrom = None

for en_page in en.allpages(limit=250,
                           apfilterredir='nonredirects',
                           apfrom=input('Enter a page to start from '
                                        'or Enter for from file').strip()
                           or startfrom):
    print(en_page)
    en_contents = en_page.read()
    tw_page = tw.page('Eng:' + en_page.title, getinfo=True)
    tran_page = tw.page('Eng:' + en_page.title + '/translate', getinfo=True)
    if hasattr(tw_page, 'missing'):
        print(tw_page, 'does not exist')
        en_norm_contents = normalize(en_contents, title=en_page.title)
        response = easygui.codebox('Confirm contents of new page:',
                                   'Confirm Edit',
                                   normalize(en_contents, title=en_page.title))
        if response is not None:
            response = response.strip() or None
        if response is not None:
            try:
                print(tw_page.edit(en_norm_contents,
                                   'Automated edit: '
                                   'Updated Test wiki copy '
                                   'of English wiki page'))
            except mwc.requests.HTTPError:
                print(' Throttled, waiting 5 seconds')
                time.sleep(5)
                print(tw_page.edit(en_norm_contents,
                                   'Automated edit: '
                                   'Updated Test wiki copy '
                                   'of English wiki page'))
            time.sleep(2)
    else:
        tw_contents = tw_page.read()
        en_norm_contents = normalize(en_contents, title=en_page.title)
        if en_norm_contents != tw_contents:
            response = easygui.codebox('View diff and confirm',
                                       'View Diff',
                                       '\n'.join(unified_diff(tw_contents
                                                              .splitlines(),
                                                              en_norm_contents
                                                              .splitlines(),
                                                              tw_page.title,
                                                              en_page.title,
                                                              lineterm='')))
            if response is not None:
                response = response.strip() or None
            if response is not None:
                try:
                    print(tw_page.edit(en_norm_contents,
                                       'Automated edit: '
                                       'Updated Test wiki copy '
                                       'of English wiki page'))
                except mwc.requests.HTTPError:
                    print(' Throttled, waiting 5 seconds')
                    time.sleep(5)
                    print(tw_page.edit(en_norm_contents,
                                       'Automated edit: '
                                       'Updated Test wiki copy '
                                       'of English wiki page'))
                time.sleep(2)
            else:
                break
        else:
            print('Not edited - contents were identical')
            time.sleep(1) #sleep less since only one request was made not two
    # Get interwiki links - credit to Apple502j for this part
    iwlinks = ['en:' + en_page.title]
    print('Getting iwlinks (see credit comment)')
    for wikilink in mwp.parse(en_contents, 0, True).ifilter_wikilinks():
        if re.match('[a-z][a-z]:.*', str(wikilink.title), re.I):
            iwlinks.append(wikilink.title)
    if hasattr(tran_page, 'missing'):
        tran_content = '{{translate\n|Eng=' \
                       + en_page.title \
                       + '\n|En=' \
                       + en_page.title \
                       + '\n'
        for iwlink in iwlinks:
            tran_content += '|' \
                            + str(iwlink).split(':', 1)[0].capitalize() \
                            + '=' \
                            + str(iwlink).split(':', 1)[1] \
                            + '\n'
        tran_content += '}}'
        tran_page.edit(tran_content,
                       'Automated edit: Created /translate page')
        print('Created /translate page')
    else:
        tran_content = tran_page.read()
        tran_mod_content = mwp.parse(tran_content, 0, True)
        tran_template = tran_mod_content.filter_templates()[0]
        for iwlink in iwlinks:
            iwlink = str(iwlink).split(':', 1)
            if not tran_template.has(iwlink[0].capitalize()):
                tran_template.add(iwlink[0].capitalize(), iwlink[1])
        if tran_mod_content != tran_content:
            tran_page.edit(str(tran_mod_content),
                           'Automated edit: Updated interwiki links')
            print('Edited tran_page')
    index(translation_index, tran_page)
