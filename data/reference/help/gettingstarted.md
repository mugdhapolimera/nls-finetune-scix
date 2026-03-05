# Gettingstarted

## Build Library

### How do you build a library?
*Note: the Getting Started series is designed to get you started with the new interface. More advanced information on libraries can be found in the [Creating and Editing a Library help page](../libraries/creating-libraries../../libraries-scix/creating-libraries) and other pages in the "SciX Libraries" sections.*

SciX libraries allow you to save collections of papers to view later. These libraries can be private (by default) or public. In addition to viewing and sorting saved papers, you can export the collection in a variety of formats, view citations and other metrics, explore visualizations such as the paper or author networks, and check for related papers.  Libraries are a popular way to build reference lists when writing papers, or keeping one's bibliography to use in a CV.

***Note: to save papers to a library, you must be logged into your SciX account.***

Add papers to a new or existing library directly from the search results. You can add all papers returned in the search to a library, or only a selection:


   <img src="/help/img/library-add.gif"  class="img-responsive" alt="a short
   animated image showing adding a paper to a library">

   <img src="/scixhelp/sciximg/scix-library-add.gif"  class="img-responsive" alt="a short
   animated image showing adding a paper to a library">




The same function is available on the abstract page of a single paper.

### Export
The contents of a library can be [exported in a variety of formats](../actions/export../../actions-scix/export), including BibTeX and AASTeX. This was designed to facilitate the development of a SciX library as a bibliography for a paper in progress, and allow its export into the appropriate format for the journal when ready.


   <img src="/help/img/library-export.png"  class="img-responsive">

   <img src="/scixhelp/sciximg/scix-library-export.gif"  class="img-responsive">

 

### Citation helper
The [library citation helper](../libraries/citation-helper) is a unique feature specifically available to help build and maintain complete collections. It's designed to evaluate the papers already in a library and suggest related papers that should possibly also be included. 


   <img src="/help/img/library-citation-helper.png"  class="img-responsive">


### Metrics: citations and reads
The [citations and read statistics](../actions/analyze../../actions-scix/analyze) for a library are available, similar to those available from the search results page or an abstract page. Click on the Metrics button within the library to view.


   <img src="/help/img/library-metrics.png"  class="img-responsive">

   <img src="/scixhelp/sciximg/scix-library-metrics.gif"  class="img-responsive">


### Visualizations: paper network, author network, word cloud
The same [visualizations](../actions/visualize../../actions-scix/visualize) available in the search results page are available within a SciX library. 


   <img src="/help/img/author_network.png"  class="img-responsive">

   <img src="/scixhelp/sciximg/scix-author_network.gif"  class="img-responsive">

## Common Name

### How do you find a paper by an author with a common name?
*Note: the Getting Started series is designed to get you started with the
new interface. More advanced information on searching can be found in
the [Search Syntax help page](../search/search-syntax../../search-scix/search-syntax) and other pages in the "Making a Query"  and "Search Results" sections.*

Finding a paper by an author with a common name, especially if you have little else to go on, can be like finding a needle in a haystack. However, there are some strategies that can help.

### Exact name matching

By default, SciX returns all relevant matches when searching for author names. For example, searching for *author:"smith, j"* will return results for J. Smith, Jane Smith, and John Smith, amongst others. To disable this synonym expansion, use the equals sign operator (=). Searching for *=author:"smith, j"* will only return results where the first initial was used in place of the full spelled-out given name. 

This can be especially helpful when a given author often uses their middle initial. For example, compare the number of results for author Y. Wang:

   <img src="/help/img/exact-name-1.png"  class="img-responsive" alt="Exact
   name matching query with full family name and given name
   initial. 5732 total search results.">
   



With those for author Y. S. Wang:


   <img src="/help/img/exact-name-2.png"  class="img-responsive" alt="Exact
   name matching query with full family name and given name and middle name
   initials. 233 total search results.">




### Filtering results

The facets are useful when trying to narrow down a large list of search results. In addition to the author facet, which allows you to include or exclude name variations of authors, try these facets. All are located in the left-hand column, unless otherwise noted:
- Collections: by default, records from all database collections (astronomy, physics, and general) are searched from the one-box modern search interface. Limit or exclude collections here as necessary
- Refereed: limit your search to refereed or non-refereed records
- Years: located in the right-hand column, the year sliders allow you to select a publication year or range of publication years to include or exclude
- Publications: if the journal or other publication name is known, select it here
- Bib Groups: some telescopes and research institutes maintain curated listings of records relevant to their institutions; these groupings are listed here
- Data: filter based on the availability of specific links to data products, such as NASA missions, archives, SIMBAD, and NED
- SIMBAD and NED Objects: filter based on a specific object 


   <img src="/help/img/filter-facets.png"  class="img-responsive"
   alt="Search results with filter facets highlighted.">


### I'm an author with a common name; how do I make my papers easier to find?

If you're an author with a common name, there are some strategies you can follow to make your papers more discoverable.

### Tips & Tricks
- Include your full name and at least your middle initial in author lists.
- If possible, use the same form of your name (e.g. initial vs. spelled-out form of your given or middle names) when publishing.
- If you've changed your name (given or family name) since you've begun publishing, email us at <a href="mailto:help@scixplorer.org">help@scixplorer.org</a><a href="mailto:adshelp@cfa.harvard.edu">adshelp@cfa.harvard.edu</a> and we can link your name variations together. Thereafter, searching for one name variation will return publications under all linked names.

### ORCID

Create an [ORCID ID](https://orcid.org/). After obtaining your ID, [claim your papers in SciX](../orcid/claiming-papers../../orcid-scix/claiming-papers). We'll do some basic checks to make sure you haven't claimed someone else's papers by mistake and link your ORCID ID to your papers within 24 hours. As part of this process, the papers you claim within SciX will automatically be pushed to your ORCID record on [orcid.org](https://orcid.org/). For current and future publications, many journals (such as ApJ) now accept ORCID IDs upon submission; ORCID IDs submitted this way will automatically populate in SciX after paper publication.

After linking your ORCID ID with your publications, users will be able to search for your papers using the syntax *orcid:XXXX-XXXX-XXXX-XXXX*. You may link to the search results using this syntax: https://ui.adsabs.harvard.eduhttps://scixplorer.org/#search/q=/search?q=orcid%3AXXXX-XXXX-XXXX-XXXX

### Public library
In some situations, [creating a library](../libraries/creating-libraries../../libraries-scix/creating-libraries), [making it public](../libraries/public-libraries../../libraries-scix/public-libraries), and sharing the link may be useful.

## Literature Search

### How do you start a literature search in SciX?

*Note: the Getting Started series is designed to get you started with the new interface. More advanced information on searching can be found in the [Second Order Queries](../search/second-order../../search-scix/second-order), [Citation Helper](../libraries/citation-helper), and [Article View](../actions/article-view../../actions-scix/article-view) help pages and other pages in the "Making a Query" and "Search Results" sections.*

Starting research on a new topic can be tricky, especially when you
don't know which papers you should be reading. How do you make sure
you've covered everything and are fully up to speed on your background
reading? SciX has some tools to help. We've divided this quick start
guide into three sections, depending on the starting point: starting
from an individual paper, from a broad topic or keyword, or from an
existing library. Read on for more.

### Starting from an individual paper

If you have one or two reference or other papers you're starting your
search with, there are a few sources of potentially related papers. To
begin, go to the abstract page for the paper. In the left column are
links for the Citations, References, and Co-Reads. Citations list
papers that cite the given paper, while References are cited in the
given paper and listed in its bibliography. Exploring both of these is
a good starting point. Also investigate papers listed under
Co-Reads. These are papers that users who read the paper in question
also read; they may be related to the original paper in a variety of
ways and can provide interesting insights. By default, the Citations,
References, and Co-Reads lists are sorted in reverse chronological
order. To re-sort or filter the results, click the button to view the
results in a search results page.


   <img src="/help/img/coreads_1.png"  class="img-responsive" alt="an
   image showing the Co-Reads links on the abstract page">

   <img src="/scixhelp/sciximg/scix-coreads_1.gif"  class="img-responsive" alt="an
   image showing the Co-Reads links on the abstract page">


   <img src="/help/img/coreads_2.png"  class="img-responsive" alt="an
   image showing the Co-Reads listing">
   
   

*Abstract page and Co-Reads for a canonical WMAP paper. Click "view
   this link in a search results page" to re-sort and filter the
   related papers.*

### Starting from a topic
If you want to know about a general topic (e.g. gravitational waves or
coronal mass ejections), there are three main methods to find related
papers: sorting, second-order search operators, and the paper network.

**Sorting**

The sort options available from the search results page are a natural
first step in exploring by topic. For many searches, the default sort
option is by publication date, with most recently published articles
first. However, other sorting options may be more useful. For example,
a search for *M31* returns most recently published articles
first. Sorting by **citation count** instead returns more highly cited
articles first. These results can be narrowed by publication year or
by other filters in the left and right columns. For a measure of more
recent popularity, try sorting by **read count**: this sorts the
results based on the papers most read or downloaded over the last 90
days.

**Second-order search operators**

The [second-order search operators](../search/second-order../../search-scix/second-order) are usable in the one-box
search box and are available as an autocomplete search term in the
search box, or for selection from the search term menu above the
search box. There are three main second-order search operators that
may be useful for literature searches:

* **trending()** This search operator returns papers recently read by
  people who are interested in the subject. For example, a search for
  M31 would return a set of papers about the Andromeda galaxy. A
  search for *trending(M31)* would return the papers recently read by
  people who had also read papers about M31. The results are returned
  sorted by score order, with the most relevant results first. Note
  that the co-reads for an individual article, described above, makes
  use of the trending() operator.

* **reviews()** This search operator returns papers that frequently
  cite relevant papers. For M31, *reviews(M31)* would return papers
  that cite many of the most relevant papers. Papers in this group may
  include (but are not necessarily) review articles or articles with
  in depth introduction sections.

* **useful()** This search operator returns papers frequently cited by
  relevant papers. Returning to Andromeda, a search for *useful(M31)*
  would return papers frequently cited in the most relevant M31
  papers. The results from this operator are generally papers about
  tools, methods, or data sets relevant to a field.


   <img src="/help/img/second-order.png"  class="img-responsive" alt="diagram showing use of the second order operators">
   
   


**Paper Network**

The [Paper Network](../actions/visualize#paper-network../../actions-scix/visualize#paper-network), available from
the Explore dropdown menu in the upper right on the search results
page, is a useful tool for exploring subtopics within a larger
search. Results from a search are sorted into subgroups based on
shared references between those records. Clicking on one of the
resulting subgroups (the colorful wedges in the visualization) shows
the papers belonging to that subgroup. At the end of the list of
subgroup papers is a short list of papers that were highly cited by
the papers within the given subgroup but that may or may not have been
included in the original search. This list of potentially relevant
papers is similar to the useful() papers above.

Note that, by default, the paper network is built from the top 400
papers in a list of results and can only be extended to include up to
1000 papers in the results list. Therefore, it is best used with a
list that has been been previously narrowed to a few hundred papers.


   <img src="/help/img/paper-network-suggested-papers.png"  class="img-responsive" alt="an
   image showing Paper Network with suggested papers">
   
   <img src="/scixhelp/sciximg/scix-paper-network-suggested-papers.png"  class="img-responsive" alt="an
   image showing Paper Network with suggested papers">
   
   

*Paper network for a search for refereed papers about the MUSE
   instrument. In this subgroup, containing instrumentation papers,
   the suggested papers at the bottom contain highly relevant
   non-refereed conference proceedings and other papers.*

### Starting from a library

If you've started to assemble a library organized around a given topic
(e.g. for a paper in progress), there are tools available to ensure
you haven't forgotten any relevant references. In addition to the
paper suggestions offered by the in-library
Paper Network,
 the [Citation Helper](../libraries/citation-helper) is
designed to find related papers. It finds up to 10 papers that are
either cited by or that cite the papers in the library, but are not
contained in the library. Its results are similar to a combination of
the useful() and reviews() operators above. The suggested papers are
sorted by score, with the most relevant papers first. If you have
write access to a library, you can select desired papers and add them
to your library within this tool.
 you can use the Explore menu to discover related papers and add them to your library.


   <img src="/help/img/citation-helper.png"  class="img-responsive" alt="an
   image showing the Citation Helper within a library">
   
   

*Example of the Citation Helper for the public library containing [refereed papers about SciX](https://ui.adsabs.harvard.edu/#/public-libraries/aI9-ox_2RNeZK-gm-4DpVQ). The top suggested papers are papers about SciX that are closely related to the papers in the library via citations and references.*

## Searching For Paper

### How do you search for a specific paper?
*Note: the Getting Started series is designed to get you started with the
new interface. More advanced information on searching can be found in
the [Search Syntax help page](../search/search-syntax../../search-scix/search-syntax) and other pages in the "Making a Query"  and "Search Results" sections.*

A common task in SciX is locating a specific paper, often for
download or for retrieval of the bibliographic data. In this case, a
user usually knows an author name (often the name of the first
author), plus a publication year. This type of search is simple, but
knowing some tips and tricks can make the process proceed more quickly
and smoothly.

### Tips
- Use fielded queries to ensure you receive the expected results.
- Use the [Classic Form](https://ui.adsabs.harvard.eduhttps://scixplorer.org/#classic-form) to automatically create fielded queries and replicate the SciX Classic look and feel. (Note: advanced and fulltext search fields are not available in the Classic Form.)
- Make use of tag auto-completion when entering fielded queries to speed up search term entry.
- It is not generally recommended that you initially search on author affiliation as a number of publishers do not provide this information to SciX. Additionally, variants on institution name may confuse the search results.

### Fielded vs. unfielded queries
The one-box search field accepts both fielded queries, where the user specifies the field being searched (such as *year:*) along with the search terms, and unfielded queries, where no search fields are explicitly specified. Unfielded queries automatically search all metadata fields; this may not produce the expected results.

We recommend that you use the field tags (e.g. *author:*) when searching for a known author and/or year of publication. However, you do not have to type the full tag or select it from the list each time you search. Auto-completion is enabled, so you can start typing the tag, then press Return to accept the auto-complete when the appropriate tag is shown. The cursor will automatically be moved to the appropriate spot within the tag to type the search term.

### Querying when author and year of publication are known
1. Click on the author tag in the Quick Field area, or start typing *author:* and press Return to accept the auto-completion.
2. Fill in the author name.
3. Do the same for the year: tag and year of publication.
4. Press Return or click the Search button to begin the search.


   <img src="/help/img/author.gif"  class="img-responsive" alt="a short
   animated image showing querying by author and year">

   <img src="/scixhelp/sciximg/scix-author.gif"  class="img-responsive" alt="a short
   animated image showing querying by author and year">


### Querying when the first author is known
Follow the same procedure as for a known author, but to trigger the first-author tag autocompletion, use the standard caret (^) operator or start typing "first author."

Note: for a first-author search using the ^ operator, you do not have to specify the author tag. Typing *^last_name* is an abbreviation for *author:"^last_name"* and will produce the expected results.


   <img src="/help/img/caret_firstauthor.gif"  class="img-responsive" alt="a short
   animated image showing querying by first author using the caret operator">

   <img src="/scixhelp/sciximg/scix-caret_firstauthor.gif"  class="img-responsive" alt="a short
   animated image showing querying by first author using the caret operator">


### Filtering
If your search by author and/or publication year returns too many results, you can use [interactive filtering](../search/filter../../search-scix/filter) to narrow down the results instead of editing your original search query. Filtering by author or publication is often useful when a paper is known. 


   <img src="/help/img/filter-facet.png"  class="img-responsive">

   <img src="/scixhelp/sciximg/scix-filter-facet.png"  class="img-responsive">
