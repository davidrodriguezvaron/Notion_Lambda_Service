// Set this to the address the digest is sent from (your SES_SENDER_EMAIL).
// While it is left as the placeholder, the script deletes nothing.
var SENDER_EMAIL = "sender@example.com";

function autoDeleteNotionEmails() {
  if (SENDER_EMAIL === "sender@example.com") {
    Logger.log("SENDER_EMAIL is not configured; nothing deleted.");
    return;
  }

  // Only emails sent by the digest sender, with subject containing "Task List",
  // that are older than 2 days. Without the from: filter any email with that
  // subject (from anyone) would be trashed.
  var query = 'from:' + SENDER_EMAIL + ' subject:"Task List" older_than:2d';
  var threads = GmailApp.search(query);

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
