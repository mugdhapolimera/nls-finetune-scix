# 

[**Introduction	1**](#introduction)

[**Identifying mentions in the SciX holdings	2**](#identifying-mentions-in-the-scix-holdings)

[Mentions from full text documents	3](#mentions-from-full-text-documents)

[Data Availability Statement sections	3](#data-availability-statement-sections)

[Anywhere else in the text	3](#anywhere-else-in-the-text)

[Related Works data	3](#related-works-data)

[Summary	3](#summary)

[**Retrieving mentions from external sources	4**](#retrieving-mentions-from-external-sources)

[Astrophysics Source Code Library	4](#astrophysics-source-code-library)

[Crossref	5](#crossref)

[DataCite	6](#datacite)

[**Technical implementation	6**](#technical-implementation)

[Back office data gathering and preparation	7](#back-office-data-gathering-and-preparation)

[Assigning mention types	8](#assigning-mention-types)

[Do we need to make a distinction between software and data mentions?	8](#do-we-need-to-make-a-distinction-between-software-and-data-mentions?)

[Pipeline processing	9](#pipeline-processing)

[Data Pipeline	9](#data-pipeline)

[Protobuf updates	10](#protobuf-updates)

[Master Pipeline	11](#master-pipeline)

[Solr representation	12](#solr-representation)

[**Tasks	13**](#tasks)

[Admin	13](#admin)

[Back Office	13](#back-office)

[Data Pipeline	13](#data-pipeline-1)

[Protobufs	13](#protobufs)

[Master Pipeline	13](#master-pipeline-1)

[Solr	14](#solr)

[**Out of scope elements	14**](#out-of-scope-elements)

# Introduction {#introduction}

We want to offer users functionality that will allow them to explore "mentions" in ways similar to how they can explore formal citations. For citations we have implemented a citation graph which supports the second-order operators citations() and references(). The end goal is to have similar functionality for "mentions"[^1], supporting discovery in a bi-directional manner, like we offer for citations.

This document focuses on the ingest and indexing of the mentions. The development of the "mentions graph" needs to be a topic for a later discussion.

Before going into details, first a definition of the context of "mentions". Essentially, a "mention" is the action of referring to an entity within the body of a publication. The **reciprocal relationship** is called "credit". The types of mentions we are interested in are those that can be expressed in the form of a URI. In the context of the implementation described here, the context is even narrower: the target of the mention has to be an entity with a corresponding record in SciX. So, essentially, the relationships can be expressed by

\[SciX ID\] \--(mentions)--\> \[SciX ID\]  
\[SciX ID\] \<--(credits)--  \[SciX ID\]

If the implementation happens before the formal introduction of the SciX ID in production, the relationship will be between bibcodes. 

While, as such, any URI can contribute to the collection of "mentions", in the current context we will restrict ourselves to mentions by means of DOI links or well-defined identifiers that can be linked to existing records. These mentions in the form of DOI links will be retrieved from the full text documents associated with SciX records and, possibly, external registries that expose such relationships. In addition to restricting ourselves to DOI links, we further restrict ourselves to DOI corresponding to either **data** or **software** and identifiers representing **grants**. 

At a later stage we can broaden any of the definitions mentioned above.

We also need to record the context of mentions. The "how" and "what" aspects of this will be discussed later.

# Identifying mentions in the SciX holdings {#identifying-mentions-in-the-scix-holdings}

There are essentially three sources within SciX that can contribute to mentions:

1. Full text documents  
   1. Data Availability Statement sections  
   2. Anywhere else in the body of the text  
2. Related Works data (generally provided by external sources)

## Mentions from full text documents {#mentions-from-full-text-documents}

### Data Availability Statement sections {#data-availability-statement-sections}

We are currently mining links from Data Availability Statement (DAS) sections for 375 journals

| Publisher | Number of journals |
| :---- | ----- |
| Springer | 191 |
| IOP | 39 |
| AAS | 5 |
| Elsevier | 108 |
| AGU | 21 |
| AMS | 11 |

Essentially what happens in this process is locating the DAS (via XML patterns) and mining all URLs in this section. The end result is an association of bibcodes and URLs. There is a separate process that attempts to attribute labels to these URLs based on some heuristics (DOI prefixes or URL patterns). If no match was found, the URL gets the vanilla label DATASOURCE.

Notes:

* This process is still pretty much in a "pilot" stage. The code needs a substantial rewrite to make it more conformant to SciX coding patterns and standards.  
* No attempt has been made, so far, to update the list of journals  
* The process does not attempt to identify whether a URL is for software or data  
* We have not yet attempted to mine grant information from the full text

### Anywhere else in the text {#anywhere-else-in-the-text}

This category will be represented by the ML work done by Stephanie and Anna.

## Related Works data {#related-works-data}

In the various categories of Related Works data, we have a (small) set of links to software and data. For all DOI links among these links, we will grab those that correspond to existing SciX records and add those to the list of mentions. These are typically relationships provided by external sources, like users; **no context is available**.

## Summary {#summary}

In the current, "low hanging fruit" approach to capturing mentions of data and software, the following sources contribute

1. Those DOIs found in DAS sections that correspond to existing SciX records  
2. Those DOIs found in Related Works links for software and data that correspond to existing SciX records

Given the fact that we want to record contextual information, the second source may need to be discarded.

# Retrieving mentions from external sources {#retrieving-mentions-from-external-sources}

This part mainly consists of identifying these external sources and means to harvest mentions from them automatically.

## Astrophysics Source Code Library {#astrophysics-source-code-library}

Mentions for software are retrieved from the Astrophysics Source Code Library (ASCL). This data is exposed by the ASCL on the following URL: [https://ascl.net/code/json](https://ascl.net/code/json)

The ASCL data has entries like the following:

 "16": {  
    "ascl\_id": "9910.005",  
    "title": "XSPEC: An X-ray spectral fitting package",  
    "credit": "Arnaud, Keith; Dorman, Ben; Gordon, Craig",  
    "abstract": "It has been over a decade since the first paper was published containing results determined using the general X-ray spectral-fitting program XSPEC. Since then XSPEC has become the most widely used program for this purpose, being the de facto standard for the ROSAT and the de jure standard for the ASCA and XTE satellites. Probably the most important features of XSPEC are the large number of theoretical models available and the facilities for adding new models.",  
    "topic\_id": "19783",  
    **"bibcode": "1999ascl.soft10005A",**  
    "views": "9947",  
    "preferred\_citation": "https://ui.adsabs.harvard.edu/abs/1996ASPC..101...17A",  
    "site\_list": \[  
      "https://heasarc.gsfc.nasa.gov/docs/xanadu/xspec/index.html"  
    \],  
    **"used\_in": \[**  
      **"https://ui.adsabs.harvard.edu/abs/2022ApJ...938L...7D"**  
    **\],**  
    **"described\_in": \[**  
      **"https://ui.adsabs.harvard.edu/abs/1996ASPC..101...17A"**  
    **\],**  
    "keywords": {  
      "4": "NASA",  
      "12": "ROSAT",  
      "13": "ASCA",  
      "16": "RXTE"  
    }  
With ASCL data, like the record shown above, we can trivially generate the required mention relationships: the bibcode representing the software highlighted in **green** and the publications that mentioned this software highlighted in **blue**.

## Crossref {#crossref}

We count the acknowledgement of grants as mentions. When available, funding information is available in Crossref metadata in sections like the following

    "funder": \[  
      {  
        "DOI": "10.13039/100000104",  
        "name": "National Aeronautics and Space Administration",  
        "doi-asserted-by": "publisher",  
        "award": \[  
          "NNX15AF53G",  
          "NNX16AB78G",  
          "NNX16AB80G",  
          "80NSSC20K0601",  
          "80NSSC19K0074"  
        \],  
        "id": \[  
          {  
            "id": "10.13039/100000104",  
            "id-type": "DOI",  
            "asserted-by": "publisher"  
          }  
        \]  
      },  
      {  
        "DOI": "10.13039/100000001",  
        "name": "National Science Foundation",  
        "doi-asserted-by": "publisher",  
        "award": \[  
          "AGS‐1702147",  
          "AGS‐1744269"  
        \],  
        "id": \[  
          {  
            "id": "10.13039/100000001",  
            "id-type": "DOI",  
            "asserted-by": "publisher"  
          }  
        \]  
      }  
    \],

The data we currently have, has been extracted from the Crossref Public Data files we downloaded. The grants information is parsed out to populate the grant field in Solr for those publications that have a record in our holdings. Next, a process checks whether these grant numbers are associated with a NASA proposal record in our system; if so, we can create a mention association as mentioned earlier, as a relationship between two ADS/SciX records.

## 

## 

## DataCite {#datacite}

DataCite metadata contains similar funding information. For example

  "fundingReferences": \[  
    {  
      "awardUri": "info:eu-repo/grantAgreement/EC/HE/101072454/",  
      "awardTitle": "MWGaiaDN: Revealing the Milky Way with Gaia",  
      "funderName": "European Commission",  
      "awardNumber": "101072454",  
      "funderIdentifier": "https://doi.org/10.13039/100018693",  
      "funderIdentifierType": "Crossref Funder ID"  
    },  
    {  
      "awardUri": "info:eu-repo/grantAgreement/UKRI/STFC/ST/W001136/1/",  
      "awardTitle": "MSSL Astrophysics Consolidated Grant 2022-25",  
      "funderName": "UK Research and Innovation",  
      "awardNumber": "ST/W001136/1",  
      "funderIdentifier": "https://doi.org/10.13039/100014013",  
      "funderIdentifierType": "Crossref Funder ID"  
    },  
    {  
      "awardUri": "info:eu-repo/grantAgreement/UKRI/UKRI/EP/X031756/1/",  
      "awardTitle": "MWGaiaDN: Revealing the Milky Way with Gaia",  
      "funderName": "UK Research and Innovation",  
      "awardNumber": "EP/X031756/1",  
      "funderIdentifier": "https://doi.org/10.13039/100014013",  
      "funderIdentifierType": "Crossref Funder ID"  
    }  
  \],

The process is similar to that for Crossref. The data we currently have, has been extracted from the DataCite Public Data files we downloaded. The grants information is parsed out to populate the grant field in Solr for those publications that have a record in our holdings. Next, a process checks whether these grant numbers are associated with a NASA proposal record in our system; if so, we can create a mention association as mentioned earlier, as a relationship between two ADS/SciX records.

# Technical implementation {#technical-implementation}

The technical implementation follows the same pattern as we use for processing citation data and involves the following layers

* Back office data gathering and preparation  
* Pipeline processing  
* Solr representation

## Back office data gathering and preparation {#back-office-data-gathering-and-preparation}

Since, unlike citation data in SciX, the mention relationship is symmetrical (i.e. the data for one directions is the direct inverse of the data in the opposite direction), we only need to generate data for one direction; the data for the opposite direction can be generated by simple inversion.   
The back office data gathering and preparation follows the current Classic indexing paradigms and patterns. The first step is the creation of a mention directory in the Classic back office architecture /proj/ads/abstracts/config/links:

/proj/ads/abstracts/config/links/mention

The selection of the name mention (singular) instead of the perhaps more intuitive mentions was guided by the desire for symmetry with how we store citations.

The typical pattern of Classic indexing is: the command mkcodes something creates an all.links file in the something subdirectory in the Classic back office architecture. This process generates that all.links file from the following sources

| .dat files | Taken "as is" |
| :---- | :---- |
| .tab files | Processed with .exe scripts into .dat files (all with same file name) |
| makefile.pre | Make file that gets executed first (make \-f makefile.pre) |

Currently, when mkcodes mention is executed, the following happens

1. Create a mapping between DOI and bibcode for all software records in SciX[^2]  
2. Create a mapping between DOI and bibcode for all data records in SciX  
3. Create a file ascl.dat that grabs all described\_in and used\_in entries from the ASCL JSON data (see above). This file contains bibcodes of journal articles in the first column and the ASCL codes mentioned in the second column  
4. Create associated\_software.dat from associated\_software.tab (see earlier)  
5. Create DataAvailabilityStatements.dat from DataAvailabilityStatements.tab (see earlier)

This process can be augmented by any other .dat or .tab file (with associated .exe script) with other contributions from mentions. The only requirement is that the .dat file is a three-column tab-separated file with the bibcode of the publication in the first column, the bibcodes of the mentioned sources in the second column and mention types in the third column (see below). We have the following (manually generated) .dat files

| DataCite.dat | Created from the RelatedIdentifiers section in DataCite metadata for those entries where the relationType is either References or IsReferencedBy. |
| :---- | :---- |
| NASAprop\_mentions.dat | Created when mkcodes grants is executed. Is contains mentions of NASA grants by publications indexed in SciX/ADS |
| NSFprop\_mentions.dat | Created when mkcodes grants is executed. Is contains mentions of NSF grants by publications indexed in SciX/ADS |

### Assigning mention types {#assigning-mention-types}

Mention types will be assigned from a taxonomy.

| Mention type | Label (proposals) | How determined? |
| :---- | :---- | :---- |
| Referenced by DOI in the DAS | DAS\_DOI | Source file name \+ link format |
| Referenced by URL in the DAS | DAS\_URL | Source file name \+ link format |
| Referenced by DOI in the main text | MAIN\_DOI | Source file name (?) \+ link format |
| Referenced by URL in the main text | MAIN\_URL | Source file name (?) \+ link format |
| From ASCL used\_in | ASCL\_USED | From ASCL data |
| From ASCL described\_in | ASCL\_DESCRIBED | From ASCL data |
| From Related Works (DOI) | EXT\_DOI | Externally submitted DOI link |
| From Related Works (URL) | EXT\_URL | Externally submitted URL link |
| From DataCite | DATACITE | From DataCite metadata |
| Mentioned grants | GRANT\_ACK | From indexed grant data |

### Do we need to make a distinction between software and data mentions? {#do-we-need-to-make-a-distinction-between-software-and-data-mentions?}

Whether we need to make this distinction in the data and the subsequent workflow through the pipelines depends on the use cases we will want to support in queries. 

If we do not specify anything in the data, i.e. the mentions (represented by the bibcodes/SciX IDs of the records mentioned) will be a mix of data and software records. So, if we run a query that is supposed to return a list of mentions, the resulting records will, in general, be a mix of software and data records. In this case, either one can be filtered out by the appropriate doctype: filter. 

Examples of envisioned functionality of second order operators

| Query | Meaning |
| :---- | :---- |
| mentions(author:"Jarmak, Stephanie" doctype:software) | The query finds all mentions of SciX software records authored by this author |
| mentions(author:"Jarmak, Stephanie" doctype:dataset) | The query finds all mentions of SciX data records authored by this author |
| credits(author:"Jarmak, Stephanie") doctype:software | This query finds all publications by this authors that credit a SciX software record |
| credits(author:"Jarmak, Stephanie") doctype:dataset | This query finds all publications by this authors that credit a SciX data record |

## Pipeline processing {#pipeline-processing}

### Data Pipeline {#data-pipeline}

The ADSDataPipeline will have to be updated to deal with mentions. The first update is to create an entry in the [file\_defs.py](https://github.com/adsabs/ADSDataPipeline/blob/master/adsdata/file_defs.py) module:

data\_files\['mention'\] \= {'path': 'links/mention/all.links', 'default\_value': \[\], 'multiline': True}  
data\_files\['credit'\] \= {'path': 'links/credit/all.links', 'default\_value': \[\], 'multiline': True}

The table below explains the various entries

| Attribute | Meaning |
| :---- | :---- |
| path | Location of the data file |
| default\_value | Default value to be assigned, if applicable |
| multiline | If True, the data file contains one entry per line |

Details can be found in file changes overview of the [Pull Request](https://github.com/adsabs/ADSDataPipeline/pull/53/files) implementing the mentions.

Below are some thoughts regarding the implementation of the mentions and credits as network to support the second order operators.

When the Data Pipeline is executed with the inclusion of metrics calculation (\--no-metrics flag turned off), we can use the internal caching functionality to calculate the credits from the mentions. When the Data Pipeline is executed this way (whether with individual bibcodes or a file with bibcodes), it [initializes](https://github.com/adsabs/ADSDataPipeline/blob/master/run.py#L95) a [memory cache](https://github.com/adsabs/ADSDataPipeline/blob/b6005d66e7f99a1ae240c80f5e4f3fa6f23355ce/adsdata/memory_cache.py#L12). We can update this memory cache to support the following calls

Cache.get('mention')  
Cache.get('credit')

To support this we need to update this part of the memory\_cache.py module:

   @classmethod  
    def get(cls, which):  
        """returns either a dict (for citation or reference) or a set (for refereed)"""  
        if cls.\_initted is False:  
            cls.init()  
        if which \== 'citation':  
            return cls.\_citation\_network.network  
        elif which \== 'reference':  
            return cls.\_reference\_network.network  
      **elif which \== 'mention':**  
            **return cls.\_mention\_network.network**  
      **elif which \== 'credit':**  
            **return cls.\_credit\_network.network**  
        elif which \== 'refereed':  
            return cls.\_refereed\_list.network  
        else:  
            raise ValueError('Cache.get called with invalid value: {}'.format(which))  
          
    @classmethod  
    def init(cls):  
        if cls.\_initted is False:  
            config \= load\_config()  
            root\_dir \= config.get('INPUT\_DATA\_ROOT', './adsdata/tests/data1/config/')  
            cls.\_reference\_network \= \_Network(root\_dir \+ network\_files\['reference'\]\['path'\])  
            cls.\_citation\_network \= \_Network(root\_dir \+ network\_files\['citation'\]\['path'\])  
            **cls.\_mention\_network \= \_Network(root\_dir \+ network\_files\['mention'\]\['path'\])**  
            **cls.\_credit\_network \= \_Network(root\_dir \+ network\_files\['credit'\]\['path'\])**  
            cls.\_refereed\_list \= \_Refereed(root\_dir \+ network\_files\['refereed'\]\['path'\])  
            cls.\_initted \= True

The \_Network method can stay unaltered. 

### Protobuf updates {#protobuf-updates}

This [Pull Request](https://github.com/adsabs/ADSPipelineMsg/pull/89/files) summarizes what was implemented.

With these new fields, the [NonBib protobuf](https://github.com/adsabs/ADSPipelineMsg/blob/master/adsmsg/protobuf/nonbibrecord_pb2.py) will need some updates. It will need entries along the lines of

   \_descriptor.FieldDescriptor(  
      name='**mention**', full\_name='**adsmsg.NonBibRecord.montion**', index=???,  
      number=12, type=9, cpp\_type=9, label=3,  
      has\_default\_value=False, default\_value=\[\],  
      message\_type=None, enum\_type=None, containing\_type=None,  
      is\_extension=False, extension\_scope=None,  
      serialized\_options=None, file=DESCRIPTOR,  create\_key=\_descriptor.\_internal\_create\_key),

 The NonBib protobuf will have to support mention, credit, mention\_count and credit\_count. In the current NonBib protobuf, there is an entry for the reference field but not for the citation field, while there are entries for citation\_count and citation\_count\_norm; does something similar need to happen in the case of mention and credit?

Similarly, changes are also required for the [Master protobuf](https://github.com/adsabs/ADSPipelineMsg/blob/master/adsmsg/protobuf/master_pb2.py)? It is confusing that [nonbib.py](http://nonbib.py) in the ADSPipelineMsg module imports the Master protobuf, but it does not do anything with it.

If we want to support mention and credit in the metrics as well, we also need to update the creation of the Metrics protobuf. This is out of scope for the current implementation.

Finally, the Data Pipeline sends the protobuf to the Master Pipeline.

### Master Pipeline {#master-pipeline}

This [Pull Request](https://github.com/adsabs/ADSMasterPipeline/pull/194/files) documents the changes to the Master Pipeline.

The Master Pipeline needs to be made aware of the new fields. For one mention, mention\_count, credit and credit\_count will need to be added [here](https://github.com/adsabs/ADSMasterPipeline/blob/24fbeecc4d6533c536fccdce98c25b9af21f8958/run.py#L619). With this addition to the fields list for args.validate, entries are needed in the [validate.py](https://github.com/adsabs/ADSMasterPipeline/blob/24fbeecc4d6533c536fccdce98c25b9af21f8958/adsmp/validate.py) module along the lines of  
       \# for mentions, only check that the total number is the same (otherwise sorting  
        \# differences can confuse it)  
        if field \== 'mention':  
            if len(f1) \!= len(f2):  
                self.logger.warn(  
                        'Bibcode {}: different numbers of mentions present in each    
                         database'.format(bibcode))  
                return False  
            else:  
                return True  
       \# allow mention\_count to be different by up to 3  
        if field \== 'mention\_count':  
            if abs(f1 \- f2) \> 3:  
                self.logger.warn(  
                    'Bibcode {}: mention\_count field is different between databases. Old:   
                    {} New: {}'.format(bibcode, f1, f2))  
                return False  
            else:  
                return True

Another module that needs to be updated in the [solr\_updater.py](https://github.com/adsabs/ADSMasterPipeline/blob/24fbeecc4d6533c536fccdce98c25b9af21f8958/adsmp/solr_updater.py) module, in particular the [extract\_data\_pipeline](https://github.com/adsabs/ADSMasterPipeline/blob/24fbeecc4d6533c536fccdce98c25b9af21f8958/adsmp/solr_updater.py#L25) method. This [dictionary](https://github.com/adsabs/ADSMasterPipeline/blob/24fbeecc4d6533c536fccdce98c25b9af21f8958/adsmp/solr_updater.py#L112) will need entries for mention, mention\_count and credit\_count. Does the credit data need to be processed in a way similar to the citation data? That seems unlikely, since the only place where the citation data is used is in the the context of metrics data.

## Solr representation {#solr-representation}

Solr will need the following fields

| Field name | Field type |
| :---- | :---- |
| mention | org.apache.solr.schema.SortableTextField |
| credit | org.apache.solr.schema.SortableTextField |
| mention\_count | org.apache.solr.schema.IntPointField |
| credit\_count | org.apache.solr.schema.IntPointField |

For both the mention and credit field, the following applies

| Flags: | Indexed | Tokenized | Stored | DocValues | UnInvertible | Multivalued | Omit Norms | Omit Term Frequencies & Positions |
| ----- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Properties | √ | √ | √ | √ | √ | √ | √ | √ |
| Schema | √ | √ | √ | √ | √ | √ | √ | √ |

For both the mention\_count and credit\_count field, the following applies

| Flags: | Indexed | Stored | DocValues | UnInvertible | Omit Norms | Omit Term Frequencies & Positions |
| ----- | :---: | :---: | :---: | :---: | :---: | :---: |
| Properties | √ | √ | √ | √ | √ | √ |
| Schema | √ | √ | √ | √ | √ | √ |

# Tasks {#tasks}

Note that the pipeline work described earlier is a “best effort”; whoever will take on this task will have to do some additional detective work.

## Admin {#admin}

- [x] ~~Verify correctness of this document~~  
- [x] ~~Discuss changes, if required~~  
- [x] ~~Decide on labels for mention types~~  
- [x] ~~Assign tasks outlined below~~  
- [x] ~~Come up with implementation plan~~

## Back Office {#back-office}

- [x] ~~Create mentions directory in Classic indexing environment~~  
- [x] ~~Create data files for sources to be incorporated~~  
- [x] ~~Create processing scripts to generate .dat files~~  
- [x] ~~Create makefile.pre to take care of downloading ASCL data~~  
- [x] ~~Implement accepted labeling~~

## Data Pipeline {#data-pipeline-1}

- [x] ~~Include data file for mentions in file\_defs.py~~  
- [x] ~~Implement the function to generate credit data from mention data~~  
- [x] ~~Implement the calculation and inclusion of mention\_count and credit\_count~~

## Protobufs {#protobufs}

- [x] ~~Update the Nonbib protobuf to support the new fields~~  
- [x] ~~Verify whether the Master protobuf needs updating and do so if required~~

## Master Pipeline {#master-pipeline-1}

- [x] ~~Implement the new fields in the validation~~  
- [x] ~~Update the solr\_updater module to include the new fields~~

## Solr {#solr}

- [x] ~~Implement the mention, credit, mention\_count and credit\_count fields in the Solr schema~~

# Out of scope elements {#out-of-scope-elements}

* Inclusion of mention types  
* Inclusion of mentions and credits in metrics  
* Support of second order operators

[^1]:  One potentially confusing linguistic fact here is that "references" in DataCite Speak (as defined in their metadata model) means what we call "mentions". Semantically speaking, the proper bidirectional relationships for formal citations are "cites" and "is cited by" and for mentions they are "references" and "is referenced by". It is probably too late in the game to align ourselves with the language the community uses.

[^2]:  We need these mappings to detect whether we have a SciX record for a given DOI