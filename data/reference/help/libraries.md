# Libraries

## Citation Helper

This option gives a list of 10 results which consists of publications that cite and/or are cited by papers in the list you just submitted, but they were not in this list. The process closely resembles the network approach of establishing "friends of friends". Assuming that the bibcodes provided are all valid, it is still possible that no results will be returned. If results are returned, they have a score associated with them. This score essentially reflects how many "friends" know these other "friends".

The envisioned use case for this is the following. While in the process of writing a paper, you maintain an **SciX Library** which represents the bibliography of your paper. When you think you are done, this tool may help you identify "missing" papers that might be considered for citation, or more simply, find papers very closely related to a set of papers that you have selected.

If there are any papers you would like to add to your library, select them an click the button "Add selected papers to this library".

## Creating Libraries

There are two ways to create an SciX library:

  1. From the [search results page](https://ui.adsabs.harvard.eduhttps://scixplorer.org/#search/q=/search?q=star), select your relevant papers, and select the **Add papers to library** button. Fill in a library name and press submit.select **Bulk Actions** and then **Add to library**. Fill in a library name and press submit.

  2. Go the **My Account** drop down and select **SciX Libraries**. Press the **Create a library****Add New Library** button.

<img class="img-responsive" src="/help/img/library_screenshot.png" alt="a screenshot of SciX search results interface showing SciX libraries button"/>

It is possible to modify the name and description of the library you have created. To do this, simply navigate to the SciX Libraries page from the **My Account** drop down, at the top right of the web interface. Once there, you can select your library of interest, and press **edit** on the attribute you would like to modify.click the gear icon to modify the attributes you would like to change.

To delete any of the records in your library, simply navigate to the library and press the red **x** next to the bibcode you do not want in the library.  To delete the entire library, navigate to the library page, click on the "View Editing Options" button and select the "Delete library" option.To delete any of the records in your library, first select the record you want to remove, then click the **Delete** button.  To delete the entire library, click the gear icon, then select the "delete library" button.  Once deleted, a library is gone forever, so click with caution!

## Library Example Martha Shapley

# Martha Betz Shapley

ISNI: [0000 0005 1344 2745](https://isni.org/isni/0000000513442745)  
Born: August 3, 1890, Kansas City, Missouri, USA  
Died: January 24, 1981, Tucson, Arizona, USA

Known as the “first lady of Harvard College Observatory” during the directorship of her husband, Harlow Shapley ([0000 0001 1027 0109](https://isni.org/isni/0000000110270109)), Martha Shapley (nee Betz) was an authority on eclipsing binaries in her own right and an accomplished mathematician. 

[Scientific Contributions](https://scixplorer.org/public-libraries/jqWiU27iTyuNgy4dd5tnQg) of Martha Shapley 

[Biographical Works](https://scixplorer.org/public-libraries/Kk-Cnxx_Qriryu0DxU6Z-g) about Martha Shapley

Keywords:  [eclipsing binary stars](https://astrothesaurus.org/uat/444), [computational astronomy](https://astrothesaurus.org/uat/293), [history of astronomy](https://astrothesaurus.org/uat/1868), [Harvard College Observatory](https://platestacks.cfa.harvard.edu/observatories), [women astronomical computers](https://platestacks.cfa.harvard.edu/women-at-hco)

## Public Libraries

You can make your library publicly viewable to non-SciX users; for example, [this profile of Martha Shapley](/help/libraries/library-example-martha-shapley)[this profile of Martha Shapley](/scixhelp/libraries-scix/library-example-martha-shapley) uses public libraries to highlight papers by and about her. 

 First, navigate to the **Manage Access** tab within your SciX Libraries section under **My Account**. Click the **Make this library public** button to make it public.First, navigate to SciX Libraries page from the **My Account** drop down, then click on the library you'd like to make public. Click on the gear icon to access the library settings, then toggle **Make library public** and click **Save** to make it public. 

This button generates a unique URL that you can give to people to view your library. You have the option to make your library private again in the future, in the same part of the interface. By default, all libraries are private.

You can also add collaborators to a library to allow other users to view, edit, and/or administrate your library. Available permissions:
* *Read Only*: Can view the contents of a private library
* *Read & Write*: Can view a library and add/remove records to it
* *Admin*: Can view a library, add/remove records, edit the library name and description, and add/remove other collaborators

To add a collaborator:
1. Go to the **Manage Access** tab and scroll to the **Collaborators** section.
2. Click the **Add Collaborator** button.1. Click the gear icon and scroll to the Collaborators section.
3. Fill out the email address of the user you'd like to add as a collaborator (they must have an SciX user account under this email address) and choose their permission level.
4. Click **Add Collaborator** to finish adding the user. The user will be emailed to notify them of their updated permissions.

Editing collaborators' permissions or revoking their access can be done directly from the **Manage Access** tab.

*Note that you must be the library owner or have admin permissions to add, edit, or remove collaborators.*

## Set Operations

Set operations allow you to perform operations on one or more libraries. To access these, click the **ActionsOperations** button in the upper right of the [main page listing all of your libraries](https://ui.adsabs.harvard.eduhttps://scixplorer.org/user/libraries/).

The ActionsOperations button will open the **Library Operations** pagewindow, where you can select one of the available set operations:
* *Union*: take the union of the primary and all of the secondary libraries. The result, which includes all papers in any of the input libraries, is saved to a new library
* *Intersection*: take the intersection of the primary and all of the secondary libraries. The result, which includes only papers present in all of the input libraries, is saved to a new library
* *Difference*: take the difference between the primary and all of the secondary libraries. The result, which includes papers present in the primary library but in none of the secondary libraries, is saved to a new library
* *Copy*: copy the contents of the source library into the target library. The target library is not emptied first; use the empty operation on the target library first in order to create a duplicate of the source library in the target library
* *Empty*: empty the source library of its contents (no secondary library is needed)

After selecting the set operation, select the primary (or source) library, and any secondary (or target) libraries, as needed. Note that more than one secondary library is allowed when taking the union, intersection, or difference; click the **Add Library** button to add another secondary library.add another secondary library as needed.

You may also choose to supply a new library name for the result of the union, intersection, or difference operations. If no name is supplied, a default name will be used, which can be edited after the library is created.

## Visualisations

Like the main search interface, you can make visualisations, look at metrics, and create exports for the bibcodes within your library. 

To do so, simply navigate to your SciX Library via the button under **My Account** and then use the sub-menu buttons **Export**, **Metrics**, and **Visualize**. You can also access the same features by using the **View this library in SciX Search Results Page**.click **View as search results** to access the **Explore** menu, including visualizations and metrics, and the **Bulk Actions** menu to export the library. 

For details on these features, look at the main [help pages](../../help/actions../../scixhelp/actions-scix).
