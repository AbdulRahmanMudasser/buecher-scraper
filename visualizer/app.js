const csvFile = '../data/books.csv';
const hiddenHeaders = new Set(['image_file']);

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length === 0) {
    return [];
  }

  const headers = parseLine(lines[0]);
  return lines.slice(1).map((line) => {
    const values = parseLine(line);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] || '';
    });
    return row;
  });
}

function parseLine(line) {
  const values = [];
  let field = '';
  let insideQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    const next = line[i + 1];

    if (char === '"') {
      if (insideQuotes && next === '"') {
        field += '"';
        i += 1;
      } else {
        insideQuotes = !insideQuotes;
      }
    } else if (char === ',' && !insideQuotes) {
      values.push(field);
      field = '';
    } else {
      field += char;
    }
  }

  values.push(field);
  return values;
}

function escapeHtml(value) {
  return value.replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderTable(rows) {
  const headers = Object.keys(rows[0] || {
    title: '',
    author: '',
    publisher: '',
    product_code: '',
    series: '',
    isbn: '',
    edition_price: '',
    sale_price: '',
    fixed_book_price: '',
    availability: '',
    publication_year: '',
    page_count: '',
    dimensions: '',
    release_date: '',
    topic: '',
    cover_image: '',
    description: '',
    url: '',
  });

  const tableHead = document.getElementById('table-head');
  const tableBody = document.getElementById('table-body');

  const visibleHeaders = headers.filter((header) => !hiddenHeaders.has(header));

  visibleHeaders.forEach((header) => {
    const th = document.createElement('th');
    th.textContent = header.replace(/_/g, ' ');
    tableHead.appendChild(th);
  });

  rows.forEach((row) => {
    const tr = document.createElement('tr');

    visibleHeaders.forEach((header) => {
      const td = document.createElement('td');

      if (header === 'cover_image') {
        const coverUrl = row.cover_image || '';
        const image = document.createElement('img');
        image.src = coverUrl;
        image.alt = row.title || 'Book cover';
        image.width = 56;
        image.height = 72;
        td.appendChild(image);
      } else if (header === 'url') {
        const link = document.createElement('a');
        link.href = row.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'View';
        td.appendChild(link);
      } else {
        td.textContent = row[header] || '';
      }

      tr.appendChild(td);
    });

    tableBody.appendChild(tr);
  });
}

function loadCsv() {
  fetch(csvFile)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Unable to load ${csvFile}`);
      }
      return response.text();
    })
    .then((text) => {
      const rows = parseCsv(text);
      renderTable(rows);
    })
    .catch((error) => {
      const body = document.getElementById('table-body');
      body.innerHTML = `<tr><td class="empty-state" colspan="1">${escapeHtml(error.message)}</td></tr>`;
    });
}

loadCsv();
