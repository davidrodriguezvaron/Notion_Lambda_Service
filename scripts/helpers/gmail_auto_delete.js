function autoDeleteNotionEmails() {
  // Looks for emails with subject containing "Task List" that are older than 2 days
  // "subject:Task List" -> Searches for subject containing these words
  // "older_than:2d" -> Older than 2 days
  var threads = GmailApp.search('subject:"Task List" older_than:2d');
  
  if (threads.length > 0) {
    Logger.log("Deleting " + threads.length + " threads.");
    // Moves them to trash
    for (var i = 0; i < threads.length; i++) {
        threads[i].moveToTrash();
    }
  } else {
    Logger.log("No old threads found to delete.");
  }
}
