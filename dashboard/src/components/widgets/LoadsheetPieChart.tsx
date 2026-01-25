import { Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  TooltipItem,
} from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

interface LoadsheetStats {
  total: number;
  completed: number;
  pending: number;
  cancelled: number;
  completion_percentage: number;
}

interface Props {
  stats: LoadsheetStats;
}

export default function LoadsheetPieChart({ stats }: Props) {
  const { completed, pending, cancelled } = stats;

  if (completed + pending + cancelled === 0) {
    return null;
  }

  const data = {
    labels: ['Tamamlanan', 'Bekleyen', 'Iptal'],
    datasets: [
      {
        data: [completed, pending, cancelled],
        backgroundColor: [
          'rgba(16, 185, 129, 0.9)',
          'rgba(245, 158, 11, 0.9)',
          'rgba(239, 68, 68, 0.9)',
        ],
        borderColor: [
          'rgba(16, 185, 129, 1)',
          'rgba(245, 158, 11, 1)',
          'rgba(239, 68, 68, 1)',
        ],
        borderWidth: 2,
        hoverOffset: 8,
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
          pointStyle: 'circle',
          font: {
            size: 12,
            family: "'Inter', sans-serif",
          },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        titleColor: '#1f2937',
        bodyColor: '#4b5563',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 12,
        titleFont: {
          size: 14,
          weight: 'bold' as const,
        },
        callbacks: {
          label: function(context: TooltipItem<'pie'>) {
            const data = context.dataset.data as number[];
            const total = data.reduce((a, b) => a + b, 0);
            const value = context.raw as number;
            const percentage = ((value / total) * 100).toFixed(1);
            return `${context.label}: ${value} fis (%${percentage})`;
          },
        },
      },
    },
  };

  return (
    <div className="card p-6 animate-fade-in">
      <div className="flex items-center gap-4 mb-6">
        <div className="stat-icon gradient-amber">
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Fis Dagilimi</h3>
          <p className="text-sm text-gray-500">Duruma gore fis sayilari</p>
        </div>
      </div>
      <div className="h-64">
        <Pie data={data} options={options} />
      </div>
    </div>
  );
}
