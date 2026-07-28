/*
 * Ekspor data tabel menjadi berkas di sisi klien.
 *
 * Dipakai tombol "Ekspor"/"Unduh" selama backend belum menyediakan endpoint
 * unduhan; saat API siap, pemanggilnya cukup diarahkan ke tautan unduhan tanpa
 * mengubah tampilan.
 *
 * Pemisah memakai titik koma karena data bernilai desimal koma (locale id-ID) —
 * Excel berbahasa Indonesia juga membaca CSV dengan pemisah ini.
 */
function escapeCell(value) {
    const text = String(value ?? '');

    return /[";\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function downloadText(
    filename,
    content,
    type = 'text/plain;charset=utf-8',
) {
    // BOM agar Excel mengenali UTF-8 dan karakter non-ASCII tidak rusak.
    const blob = new Blob([String.fromCharCode(0xfeff) + content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

export function downloadCsv(filename, headers, rows) {
    const lines = [headers, ...rows].map((row) =>
        row.map(escapeCell).join(';'),
    );

    downloadText(filename, lines.join('\r\n'), 'text/csv;charset=utf-8');
}
