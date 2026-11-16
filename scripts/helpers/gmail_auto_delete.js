/**
 * Moves old task digest emails to the trash.
 *
 * Subjects look like "Tareas: 2 vencidas, 3 hoy, 4 próximas" (current format)
 * or "Task List: 3 Items Pending" (old format, kept so old emails are cleaned).
 * Only emails from SENDER_EMAIL are considered, and the subject is checked
 * again in code because Gmail search ignores punctuation.
 */

// Set this to the address the digest is sent from (your SES_SENDER_EMAIL).
// While it is left as the placeholder, the script deletes nothing.
var SENDER_EMAIL = "sender@example.com";
var MAX_AGE = "2d";
var SUBJECT_PREFIXES = ["Tareas:", "Task List:"];

function autoDeleteNotionEmails() {
  if (SENDER_EMAIL === "sender@example.com") {
    Logger.log("SENDER_EMAIL is not configured; nothing deleted.");
    return;
  }

  // Without the from: filter any email with these words in the subject
  // (from anyone) could be trashed.
  var query =
    "from:" + SENDER_EMAIL +
    ' (subject:"Tareas" OR subject:"Task List") older_than:' + MAX_AGE;
  var threads = GmailApp.search(query);
  var deleted = 0;

  for (var i = 0; i < threads.length; i++) {
    var subject = threads[i].getFirstMessageSubject() || "";
    var matches = SUBJECT_PREFIXES.some(function (prefix) {
      return subject.indexOf(prefix) === 0;
    });
    if (matches) {
      threads[i].moveToTrash();
      deleted++;
    }
  }

  Logger.log(deleted > 0 ? "Deleted " + deleted + " threads." : "No old threads found to delete.");
}
