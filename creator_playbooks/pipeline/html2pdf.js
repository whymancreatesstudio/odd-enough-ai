// usage: node html2pdf.js in.html out.pdf "Header title"
const { chromium } = require('playwright');
const [, , inp, out, title] = process.argv;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + require('path').resolve(inp), { waitUntil: 'load' });
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  await p.pdf({ path: out, format: 'Letter', printBackground: true, displayHeaderFooter: true,
    margin: { top: '18mm', bottom: '18mm', left: '16mm', right: '16mm' },
    headerTemplate: `<div style="font-size:8px;color:#777;width:100%;text-align:center">${esc(title)}</div>`,
    footerTemplate: `<div style="font-size:8px;color:#777;width:100%;text-align:center"><span class="pageNumber"></span> of <span class="totalPages"></span></div>` });
  await b.close();
})();
