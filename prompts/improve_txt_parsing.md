I would like to optimize the photo capture capabilities of this application. they currently sort of work, but not very well.  Initially, I was taking photos of book covers.  I have found that book covers are way too different, creative, colorful, hard to parse compared to the title page of a book.   So let's focus on being about to capture and properly categorize all the text that is found in images of Book title pages.  I have loaded a zip file of such images into /photos. 

Using these 4 images, some new methods for improved text capture can be added to the application.

## Descriptions of the files

**IMG_20260517_125327539.jpg**
The image in this file is upside-down: 
Be sure that images captured at different angles can still be parsed. 

**IMG_20260517_125312395.jpg**
This image has a very clear Title, Author, and Publisher, but the page is thin and a little transparent and some faint text from the next page shows through a little.  This text is unimportant and should not be parsed.  

**IMG_20260517_125431665.jpg**
This image includes some graphical elements, the title is very long. 

**IMG_20260517_125456203.jpg**
This image has a clear title, and 2 editors.  If no authors are listed, then editors are cosidered authors.  

## More general rules about parsing text on title pages

Title pages *always* lists a Title. 
Title pages *usually* lists one or more Authors.
Title pages *usually* lists the Publisher. 
Title pages *never* lists a Genre. 
Title pages *never* lists a Page Count. 
Title pages *rarely* lists a Year. 
Title pages *rarely* lists an ISBN. 
The Notes field in the database entry can be used to save any other information parsed that does not seem to fit in the other fields. 

Every field does *not* need to be populated.
The only *required* field is Title.



