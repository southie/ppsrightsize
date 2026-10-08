"""rightsizing-scenario-explorer.html: GoatCounter page-view counting (cookieless; no personal data stored).
Counts the page path only, not the #custom=... part of shared scenario links. index.html is left without the tag:
it forwards here at once, so counting it too would count each visit twice. The tag goes in <head> because
scripts/test_explorer.js takes the page script from the last </script> in the file.
Safe to rerun.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
TAG = '<script data-goatcounter="https://southie.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>'
html = open(PAGE, encoding='utf-8').read()
if 'data-goatcounter' in html:
    print('already present')
else:
    assert html.count('</head>') == 1
    html = html.replace('</head>', TAG + '\n</head>')
    open(PAGE, 'w', encoding='utf-8', newline='\r\n').write(html)
    print('added GoatCounter tag to', os.path.basename(PAGE))
