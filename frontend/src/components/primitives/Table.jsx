import React from 'react';

export default function Table({
  columns = [],
  rows = [],
  className = '',
}) {
  return (
    <div className={`w-full overflow-x-auto border border-transit-border rounded-panel bg-white ${className}`}>
      <table className="w-full text-left text-sm border-collapse">
        <thead>
          <tr className="border-b border-transit-border bg-transit-bg/70 text-xs text-transit-textMuted uppercase tracking-wider font-semibold">
            {columns.map((col, idx) => (
              <th
                key={col.key || idx}
                scope="col"
                className={`py-3 px-3.5 ${idx === 0 ? 'sticky left-0 bg-transit-bg z-10 font-bold text-navy' : ''}`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-transit-borderSubtle">
          {rows.map((row, rIdx) => (
            <tr key={row.key || rIdx} className="hover:bg-transit-bg/40 transition-colors">
              {columns.map((col, cIdx) => (
                <td
                  key={col.key || cIdx}
                  className={`py-3 px-3.5 text-transit-text ${cIdx === 0 ? 'sticky left-0 bg-white z-10 font-medium text-navy border-r border-transit-borderSubtle' : 'tabular-nums'}`}
                >
                  {row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
