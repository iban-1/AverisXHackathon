const fs = require("fs");
require("./pipeline.js");

const demoJsSrc = fs.readFileSync("demo_data.js", "utf-8");
const demo = JSON.parse(demoJsSrc.replace(/^window\.SDOC_DEMO_DATA = /, "").replace(/;\s*$/, ""));
const pySubmission = JSON.parse(fs.readFileSync("../submission.json", "utf-8"));

let mismatches = 0;
let checked = 0;

for (const email of demo.emails) {
  const jsResult = SDOC.processEmail(email, demo.attachments);
  const pyResult = pySubmission[email.email_id];
  checked++;

  const jsDefects = [...jsResult.defect_fields].sort().join(",");
  const pyDefects = [...(pyResult.defect_fields || [])].sort().join(",");

  const same =
    jsResult.category === pyResult.category &&
    jsResult.status === pyResult.status &&
    jsResult.review_reason === pyResult.review_reason &&
    jsResult.has_defect === pyResult.has_defect &&
    jsDefects === pyDefects;

  if (!same) {
    mismatches++;
    if (mismatches <= 15) {
      console.log(email.email_id);
      console.log("  py:", JSON.stringify(pyResult));
      console.log("  js:", JSON.stringify(jsResult));
    }
  }
}

console.log(`\n${checked} emails checked, ${mismatches} mismatches (JS vs Python)`);
