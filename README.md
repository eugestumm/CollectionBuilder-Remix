# CollectionBuilder-Remix

A free, beginner-friendly way to build from monolingual to bilingual (or multilingual) digital collections or exhibit sites, powered entirely by a **Google Spreadsheet** and hosted for free on [GitHub Pages](https://pages.github.com/). CB-Remix is designed so you can run it from very limited hardware, including a smartphone with a web browser.

CollectionBuilder-Remix ("CB-Remix") is a community interface built on top of [CollectionBuilder](https://collectionbuilder.github.io/) — specifically, it descends from [CollectionBuilder-GH](https://github.com/CollectionBuilder/collectionbuilder-gh), remixed with the live, collaborative spreadsheet-first workflow of CollectionBuilder-Sheets. See [`docs/about-collectionbuilder-remix.md`](docs/about-collectionbuilder-remix.md) for the full story, including its roots in the [Piñata Catalog](https://github.com/gbventura/pinatabooks) and the [Bajubá Digital Archive](https://github.com/eugestumm/BajubaDigitalArchive).

**Live example:** <https://eugestumm.github.io/CollectionBuilder-Remix/>

## What You'll Need

- A folder of digital objects — JPEGs, PDFs, MP3s, or links to video hosted on YouTube or Vimeo
- A free Google account (for the spreadsheet)
- A free GitHub account (for hosting)
- A browser — a phone is enough

No Jekyll installation, no command line, and no local software are required to run a CB-Remix site day to day.

## Build a Digital Collection

1. **Copy the [CollectionBuilder-Remix spreadsheet template](https://docs.google.com/spreadsheets/d/1DxNWMSS-z1ooxUMRHRvKrL-s-dQNc5CNmYu9mrICRZo/edit?usp=sharing)** into your own Google Drive, and fill in your metadata.
2. **Publish the spreadsheet to the web** as an **OpenDocument Spreadsheet (.ods)** — not CSV — via *File → Share → Publish to web*.
3. **Click the green "Use this template" button** on this repository to create your own copy.
4. **Paste your published spreadsheet link** into `PASTE_YOUR_GOOGLE_SPREADSHEET_LINK_HERE.txt` in your new repository.
5. **Run the "Sync content from Spreadsheet" workflow** under the repository's **Actions** tab. This pulls your metadata in and generates the site's data files.
6. **Enable GitHub Pages** under **Settings → Pages** (source: `main` branch, `/root` folder).

Full step-by-step instructions, screenshots, and troubleshooting: [`docs/collectionbuilder-remix-walkthrough.md`](docs/collectionbuilder-remix-walkthrough.md).

**Keeping your site updated:** editing the spreadsheet alone does not update your live site. Every time you add or change metadata, re-run **Sync content from Spreadsheet** from the Actions tab to publish those changes.

## A Note on Scale

Like CollectionBuilder-GH, CB-Remix runs on GitHub Pages, which makes it best suited to small and medium collections with reasonably sized images — GitHub repositories are capped at 1GB. For larger collections or deeper customization needs, look at [CollectionBuilder-CSV](https://github.com/CollectionBuilder/collectionbuilder-csv) instead.

## Minimal Computing

CB-Remix follows the [minimal computing](https://go-dh.github.io/mincomp/) principles at the heart of the whole CollectionBuilder family — sustainable, low-barrier tools that put ownership of a site in the hands of the people building it. CB-Remix pushes that further: after initial setup, GitHub is only needed to paste connect the Google Spreadsheet, upload object files, and run the sync workflow. Everything else — adding items, writing pages, translating content, fixing typos — happens in the spreadsheet itself, making it possible to build and maintain a bilingual digital collection using nothing but a phone.

## CollectionBuilder

<https://collectionbuilder.github.io/>

CollectionBuilder is a project of University of Idaho Library's [Digital Initiatives](https://www.lib.uidaho.edu/digital/) and the [Center for Digital Inquiry and Learning](https://cdil.lib.uidaho.edu) (CDIL), following the [Lib-Static](https://lib-static.github.io/) methodology. Powered by the open source static site generator [Jekyll](https://jekyllrb.com/) and a modern static web stack, it puts collection metadata to work building beautiful sites.

The base theme is built with [Bootstrap](https://getbootstrap.com/). Metadata visualizations use open source libraries including [DataTables](https://datatables.net/), [Leafletjs](http://leafletjs.com/), [Spotlight gallery](https://github.com/nextapps-de/spotlight), [lazysizes](https://github.com/aFarkas/lazysizes), and [Lunr.js](https://lunrjs.com/). Object metadata is exposed using [Schema.org](http://schema.org) and [Open Graph protocol](http://ogp.me/) standards.

General CollectionBuilder questions can be directed to the [CollectionBuilder discussion forum](https://github.com/CollectionBuilder/collectionbuilder.github.io/discussions) or **collectionbuilder.team@gmail.com**.

## License & Citation

CollectionBuilder-Remix code is licensed [MIT](LICENSE).

If you use CollectionBuilder-Remix in your own work, please cite it — see [`CITATION.cff`](CITATION.cff) for the full citation, including its lineage through CollectionBuilder-GH, the Piñata Catalog, and the Bajubá Digital Archive.

This project's own documentation and general web content follow the parent CollectionBuilder project's convention of [Creative Commons Attribution-ShareAlike 4.0 International](http://creativecommons.org/licenses/by-sa/4.0/) licensing. This does **not** cover any objects or images used in a digital collection built with this template, which may carry their own individual licenses described by each item's `rights` field. It also does not cover external dependencies included under `assets/lib`, which are covered by their own individual licenses.
