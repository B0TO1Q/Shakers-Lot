# Shaker's Lot Map

A live, touch-first map of the Shaker's Family Ford / Lincoln lot at 831 Straits Turnpike, Watertown, CT.

The whole app is a single page: `index.html`.

## What it does
- Plan of the lot traced from aerial photos: every zone, the building interior (shop, showroom, service drive), signs and landmarks
- Tap a zone to work in it full screen; drag cars between spots or into the Holding tray
- Each car shows its real Ford / Lincoln paint color with a status stripe (Available, Sold, Service, Hold, Demo)
- Key tracking with a hand-off log and spreadsheet export
- Mileage and a 0–500 mi "miles till E" meter, with a low-fuel flag
- Buyers Guide photos and printing for used units
- vAuto check: import the daily vAuto inventory export (CSV or Excel) and see what's flagged — cars not found on the lot, cars missing from vAuto, too few photos, no price, aging, sold but still listed, no Buyers Guide photo. The import stays on the device; no API
- The Ark: storm lockdown. Lines up the most valuable cars to move inside (shop, detail, showroom, service drive), remembers where each came from, and walks you through putting them back after
- A 3D view (with seasonal colors) and layouts for phone, tablet and desktop

## Running it
Open `index.html` in a browser, or serve the folder with any static host (for example GitHub Pages).

Live sync between devices, sticker scanning, sign-in names and file saving use features of the Claude artifact viewer. Opened on its own, the page still works but saves to the device it's on.
