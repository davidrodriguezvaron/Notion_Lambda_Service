/**
 * Moves old task digest emails to the trash.
 *
 * Subjects look like "Tareas: 2 vencidas, 3 hoy, 4 próximas" (current format)
 * or "Task List: 3 Items Pending" (old format, kept so old emails are cleaned).
 * Gmail search ignores punctuation, so the search is broad and the subject is
 * checked again in code to avoid deleting unrelated emails that mention "Tareas".
 */
var MAX_AGE = '2d';
var SUBJECT_PREFIXES = ['Tareas:', 'Task List:'];

function autoDeleteNotionEmails() {
  var query = '(subject:"Tareas" OR subject:"Task List") older_than:' + MAX_AGE;
  var threads = GmailApp.search(query);
  var deleted = 0;

  for (var i = 0; i < threads.length; i++) {
    var subject = threads[i].getFirstMessageSubject() || '';
    var matches = SUBJECT_PREFIXES.some(function (prefix) {
      return subject.indexOf(prefix) === 0;
    });
    if (matches) {
      threads[i].moveToTrash();
      deleted++;
    }
  }

  Logger.log(deleted > 0 ? 'Deleted ' + deleted + ' threads.' : 'No old threads found to delete.');
}
