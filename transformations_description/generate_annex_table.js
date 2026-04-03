const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, VerticalAlign,
  PageOrientation, HeadingLevel
} = require('docx');
const fs = require('fs');

const rows = JSON.parse(fs.readFileSync('../transformations_description/annex_data.json', 'utf8'));

const pwLabels = (rows[0]?.pathways ?? []).map(p => p.label);
const numPw = pwLabels.length;

const TABLE_WIDTH    = 15120;
const COL_TRANSFORM  = 2200;
const COL_POLICY     = 4520;
const PW_COL_WIDTH   = Math.floor((TABLE_WIDTH - COL_TRANSFORM - COL_POLICY) / numPw);

const FONT_SIZE = 17;

const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };

const PAD = { top: 40, bottom: 40, left: 80, right: 80 };

function run(text, opts = {}) {
  return new TextRun({ text, font: "Times New Roman", size: FONT_SIZE, color: "000000", ...opts });
}
function para(children, align = AlignmentType.LEFT) {
  return new Paragraph({ alignment: align, spacing: { before: 20, after: 20 }, children });
}

function headerCell(text, width) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders,
    margins: PAD,
    verticalAlign: VerticalAlign.CENTER,
    children: [para([run(text, { bold: true, size: FONT_SIZE })], AlignmentType.CENTER)],
  });
}

const headerChildren = [
  headerCell("Transformation",     COL_TRANSFORM),
  headerCell("Policy Description", COL_POLICY),
  ...pwLabels.map(label => headerCell(label, PW_COL_WIDTH)),
];

const headerRow = new TableRow({ tableHeader: true, children: headerChildren });

const totalCols = 2 + numPw;

function sectorHeaderRow(label) {
  return new TableRow({
    children: [new TableCell({
      columnSpan: totalCols,
      width:   { size: TABLE_WIDTH, type: WidthType.DXA },
      borders,
      margins: PAD,
      verticalAlign: VerticalAlign.CENTER,
      children: [para([run(label, { bold: true, size: FONT_SIZE })], AlignmentType.LEFT)],
    })],
  });
}

function dataCell(text, width) {
  return new TableCell({
    width:   { size: width, type: WidthType.DXA },
    borders,
    margins: PAD,
    verticalAlign: VerticalAlign.TOP,
    children: [para([run(text, { size: FONT_SIZE })])],
  });
}

function groupBySector(rows) {
  const groups = [];
  let current = null;
  for (const row of rows) {
    if (!current || current.label !== row.subsector_label) {
      current = { label: row.subsector_label, rows: [] };
      groups.push(current);
    }
    current.rows.push(row);
  }
  return groups;
}

const tableRows = [headerRow];
const groups = groupBySector(rows);

groups.forEach((group) => {
  tableRows.push(sectorHeaderRow(group.label));

  group.rows.forEach((row) => {
    const children = [
      dataCell(row.transformation_name, COL_TRANSFORM),
      dataCell(row.policy_description,  COL_POLICY),
      ...(row.pathways ?? []).map(p => dataCell(p.text, PW_COL_WIDTH)),
    ];
    tableRows.push(new TableRow({ children }));
  });
});

const columnWidths = [COL_TRANSFORM, COL_POLICY, ...Array(numPw).fill(PW_COL_WIDTH)];

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "Times New Roman", size: FONT_SIZE, color: "000000" } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: {
          width:       15840,
          height:      12240,
          orientation: PageOrientation.LANDSCAPE,
        },
        margin: { top: 851, right: 851, bottom: 851, left: 851 },
      },
    },
    children: [
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun({
          text: "Annex: Transformation Parameters by Pathway",
          font: "Times New Roman", size: 28, bold: true, color: "000000",
        })],
      }),
      new Paragraph({
        children: [],
        spacing: { after: 200 },
      }),
      new Table({
        width:        { size: TABLE_WIDTH, type: WidthType.DXA },
        columnWidths,
        rows:         tableRows,
      }),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('../transformations_description/annex_transformations_Uganda.docx', buf);
  console.log('Done → annex_transformations.docx');
});
