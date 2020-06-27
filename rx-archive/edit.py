from datetime import datetime

try:
    from config import config_page_name
except ModuleNotFoundError:
    raise ModuleNotFoundError("Please copy config.sample.py as config.py, setting up, and try again.")

import json
import os
import re
import time
import mwparserfromhell
import pywikibot

defaultTime = datetime(1, 1, 1)
os.environ['PYWIKIBOT_DIR'] = os.path.dirname(os.path.realpath(__file__))

site = pywikibot.Site()
site.login()

config_page = pywikibot.Page(site, config_page_name)
cfg = config_page.text
cfg = json.loads(cfg)
print(json.dumps(cfg, indent=4, ensure_ascii=False))

if not cfg["enable"]:
    exit("disabled")

rxpage = pywikibot.Page(site, cfg["main_page_name"])
text = rxpage.text

wikicode = mwparserfromhell.parse(text)

archivelist = {}
count = 0

for template in wikicode.filter_templates():
    if template.name.lower() == "status2":
        if template.has(1):
            status = template.get(1)
        else:
            status = "(empty)"
        print(f"Status: {status}")
        if status in cfg["publicizing_status"]:
            publicizing = True
            print("Publicizing...")
            break
        elif status in cfg["done_status"]:
            processed = True
            print("Processed.")
            break

lasttime = datetime(1, 1, 1)
for m in re.findall(r"(\d{4})年(\d{1,2})月(\d{1,2})日 \(.\) (\d{2}):(\d{2}) \(UTC\)", str(wikicode)):
    d = datetime(int(m[0]), int(m[1]), int(m[2]), int(m[3]), int(m[4]))
    lasttime = max(lasttime, d)
print(f"var: lasttime: {lasttime}")

processed = False
if re.search(cfg["processed_regex"], str(wikicode)) and not re.search(cfg["not_processed_regex"], str(wikicode)):
    processed = True
    print("Processed.")
else:
    print("Not processed.")

t1 = time.time() - lasttime.timestamp()
if (processed and t1 > cfg["time_to_live_for_processed"]) or (not processed and t1 > cfg["time_to_live_for_not_processed"]) and (lasttime != datetime(1, 1, 1)):
    target = (lasttime.year, lasttime.month)

if ((processed and not publicizing and t1 > cfg["time_to_live_for_processed"]) or (not processed and not publicizing and t1 > cfg["time_to_live_for_not_processed"])) and lasttime != datetime(1, 1, 1):
    target = (lasttime.year, lasttime.month)
    if target not in archivelist:
        archivelist[target] = []
    archivestr = str(wikicode).strip()
    archivestr = re.sub(
        r"{{bot-directive-archiver\|no-archive-begin}}[\s\S]+?{{bot-directive-archiver\|no-archive-end}}\n?", "", archivestr)
    archivelist[target].append(archivestr)
    count += 1
    wikicode.remove(wikicode)
    print("Archive to " + str(target))
    
pywikibot.showDiff(rxpage.text, text)
rxpage.text = text
summary = cfg["main_page_summary"].format(count)
print(summary)
rxpage.save(summary=summary, minor=False)

for target in archivelist:
    archivepage = pywikibot.Page(site, cfg["archive_page_name"].format(target[0], target[1]))
    text = archivepage.text
    print(archivepage.title())
    if not archivepage.exists():
        text = cfg["archive_page_preload"]
    text += "\n\n" + "\n\n".join(archivelist[target])

    pywikibot.showDiff(archivepage.text, text)
    archivepage.text = text
    summary = cfg["archive_page_summary"].format(len(archivelist[target]))
    print(summary)
    archivepage.save(summary=summary, minor=False)
