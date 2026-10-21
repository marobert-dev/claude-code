// One entry per page: the navigation tree and the search results are built from this list by
// assets/manual.js. parent = the file of the page this one sits under ("" = top level).
// keywords = the exact on-screen labels and words a reader might search for, in this folder's language.
window.MANUAL = {
  labels: {
    navigation: "Pages of the manual",
    noResults: "Nothing found. Try another word."
  },
  pages: [
    { file: "index.html", title: "Start here", parent: "", keywords: "home start", summary: "What this app does and where to begin." }
  ]
};
