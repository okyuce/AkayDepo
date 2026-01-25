import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TooltipItem,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface StationSummary {
  station_id: string;
  station_name: string;
  territory_count: number;
  total_carton: number;
  completed_carton: number;
  progress_percent: number;
}

interface Props {
  stations: StationSummary[];
}

export default function StationBarChart({ stations }: Props) {
  if (stations.length === 0) {
    return null;
  }

  const data = {
    labels: stations.map(s => s.station_name.replace('İstasyon-', 'S').replace('AnaStok', 'Ana')),
    datasets: [
      {
        label: 'Tamamlanan',
        data: stations.map(s => s.completed_carton),
        backgroundColor: 'rgba(124, 58, 237, 0.9)',
        borderColor: 'rgba(124, 58, 237, 1)',
        borderWidth: 0,
        borderRadius: 6,
        borderSkipped: false,
      },
      {
        label: 'Kalan',
        data: stations.map(s => s.total_carton - s.completed_carton),
        backgroundColor: 'rgba(229, 231, 235, 0.9)',
        borderColor: 'rgba(229, 231, 235, 1)',
        borderWidth: 0,
        borderRadius: 6,
        borderSkipped: false,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          padding: 20,
          usePointStyle: true,
          pointStyle: 'rect',
          font: {
            size: 12,
            family: "'Inter', sans-serif",
          },
        },
      },
      title: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        titleColor: '#1f2937',
        bodyColor: '#4b5563',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 12,
        mode: 'index' as const,
        intersect: false,
        titleFont: {
          size: 14,
          weight: 'bold' as const,
        },
        callbacks: {
          label: function(context: TooltipItem<'bar'>) {
            const label = context.dataset.label || '';
            const value = context.raw as number;
            return `${label}: ${value.toLocaleString('tr-TR')} karton`;
          },
        },
      },
    },
    scales: {
      x: {
        stacked: true,
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 11,
            family: "'Inter', sans-serif",
          },
        },
      },
      y: {
        stacked: true,
        beginAtZero: true,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
        ticks: {
          font: {
            size: 11,
            family: "'Inter', sans-serif",
          },
          callback: function(value: string | number) {
            return Number(value).toLocaleString('tr-TR');
          },
        },
        title: {
          display: true,
          text: 'Karton',
          font: {
            size: 12,
            family: "'Inter', sans-serif",
            weight: 'normal' as const,
          },
          color: '#6b7280',
        },
      },
    },
  };

  return (
    <div className="card p-6 animate-fade-in">
      <div className="flex items-center gap-4 mb-6">
        <div className="stat-icon gradient-info">
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800">İstasyon Karton Durumu</h3>
          <p className="text-sm text-gray-500">İstasyon bazında karton dağılımı</p>
        </div>
      </div>
      <div className="h-72">
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}
