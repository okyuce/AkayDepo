/**
 * PrintLabel — Zebra termal yazıcıya gönderilecek etiket layout'u.
 * 72mm genişlik (iMZ320 / ZQ320 max), her zaman LIGHT mode.
 * html2canvas ile PNG'ye render edilir, Web Share API ile Setup Utility'e gönderilir.
 */
import { forwardRef } from 'react';

export interface PrintLabelLine {
  product_code: string;
  product_name: string;
  qty_carton: number;
  qty_pack: number;
}

export interface PrintLabelData {
  loadsheet_no: number;
  route_order: number;
  package_number: string;
  dealer_code: string;
  dealer_name: string;
  territory_code?: string;
  territory_name?: string;
  lines: PrintLabelLine[];
  total_carton: number;
  total_pack: number;
}

interface PrintLabelProps {
  data: PrintLabelData;
}

const PrintLabel = forwardRef<HTMLDivElement, PrintLabelProps>(({ data }, ref) => {
  const territory = data.territory_code
    ? `${data.territory_code}${data.territory_name ? ' - ' + data.territory_name : ''}`
    : '';

  return (
    <div
      ref={ref}
      style={{
        width: '576px',
        background: '#ffffff',
        color: '#000000',
        fontFamily: '"Helvetica Neue", Arial, sans-serif',
        padding: '16px 14px',
        boxSizing: 'border-box',
        lineHeight: 1.25,
      }}
    >
      {data.route_order ? (
        <div style={{ textAlign: 'center', fontSize: '30px', fontWeight: 800, marginBottom: '2px' }}>
          RUT {data.route_order}
        </div>
      ) : null}
      <div style={{ textAlign: 'center', fontSize: '20px', fontWeight: 800, marginBottom: '6px' }}>
        FIŞ-{data.loadsheet_no}
      </div>
      <div style={{ textAlign: 'center', fontSize: '16px', fontWeight: 600, marginBottom: '10px' }}>
        {data.package_number}
      </div>

      <div style={{ borderTop: '2px solid #000', borderBottom: '2px solid #000', padding: '8px 0', marginBottom: '8px' }}>
        <div style={{ fontSize: '22px', fontWeight: 800 }}>{data.dealer_name}</div>
        <div style={{ fontSize: '15px', fontWeight: 600, marginTop: '2px' }}>{data.dealer_code}</div>
        {territory && (
          <div style={{ fontSize: '14px', fontWeight: 500, marginTop: '4px' }}>{territory}</div>
        )}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '16px' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #000' }}>
            <th style={{ textAlign: 'left', padding: '4px 2px', fontWeight: 800, fontSize: '14px' }}>ÜRÜN</th>
            <th style={{ textAlign: 'right', padding: '4px 2px', fontWeight: 800, fontSize: '14px', width: '70px' }}>KRT</th>
            <th style={{ textAlign: 'right', padding: '4px 2px', fontWeight: 800, fontSize: '14px', width: '70px' }}>PKT</th>
          </tr>
        </thead>
        <tbody>
          {data.lines.map((line, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid #999' }}>
              <td style={{ padding: '6px 2px', fontWeight: 600, lineHeight: 1.2 }}>{line.product_name}</td>
              <td style={{ padding: '6px 2px', textAlign: 'right', fontWeight: 700 }}>
                {line.qty_carton || ''}
              </td>
              <td style={{ padding: '6px 2px', textAlign: 'right', fontWeight: 700 }}>
                {line.qty_pack || ''}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: '2px solid #000' }}>
            <td style={{ padding: '8px 2px', fontWeight: 800, fontSize: '18px' }}>TOPLAM</td>
            <td style={{ padding: '8px 2px', textAlign: 'right', fontWeight: 800, fontSize: '18px' }}>{data.total_carton}</td>
            <td style={{ padding: '8px 2px', textAlign: 'right', fontWeight: 800, fontSize: '18px' }}>
              {data.total_pack || ''}
            </td>
          </tr>
        </tfoot>
      </table>

      <div style={{ marginTop: '16px', height: '24px' }} />
    </div>
  );
});

PrintLabel.displayName = 'PrintLabel';
export default PrintLabel;
