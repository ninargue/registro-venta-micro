interface DailyReportDateFilterProps {
  selectedDate: string;
  timezone?: string;
  onDateChange: (newDate: string) => void;
}

export function DailyReportDateFilter({
  selectedDate,
  timezone,
  onDateChange,
}: DailyReportDateFilterProps) {
  return (
    <section
      aria-label="Filtro de fecha del reporte"
      className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border-light bg-surface-light p-4 dark:border-border-dark dark:bg-surface-dark"
    >
      <div className="flex flex-wrap items-center gap-3">
        <label
          htmlFor="daily-report-date-input"
          className="text-sm font-medium text-text-light dark:text-text-dark"
        >
          Fecha del reporte
        </label>
        <input
          id="daily-report-date-input"
          type="date"
          value={selectedDate}
          onChange={(event) => {
            onDateChange(event.target.value);
          }}
          className="touch-target rounded-lg border border-border-light bg-background-light px-3 py-2 text-sm font-medium text-text-light focus:outline-2 focus:outline-primary dark:border-border-dark dark:bg-background-dark dark:text-text-dark"
        />
      </div>

      {timezone ? (
        <div className="flex items-center gap-2 text-xs text-text-muted-light dark:text-text-muted-dark">
          <span>Zona horaria:</span>
          <span className="rounded-md bg-primary-light px-2.5 py-1 font-medium text-primary-dark">
            {timezone}
          </span>
        </div>
      ) : null}
    </section>
  );
}
