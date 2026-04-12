<?php

namespace App\Services;

use App\Models\CampanhaMetric;
use App\Models\UploadCampanha;
use Carbon\Carbon;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Storage;
use PhpOffice\PhpSpreadsheet\IOFactory;
use PhpOffice\PhpSpreadsheet\Reader\Csv;
use RuntimeException;

class CampanhaService
{
    public const COLUMN_ALIASES = [
        'campaign_name' => ['campaign name', 'nome da campanha', 'campanha', 'campaign', 'ad set name', 'anúncios', 'anuncios', 'ad name'],
        'date' => ['date', 'data', 'day', 'dia', 'reporting starts', 'reporting ends', 'início dos relatórios', 'inicio dos relatórios', 'término dos relatórios', 'termino dos relatórios'],
        'amount_spent' => ['amount spent', 'valor gasto', 'gasto', 'investimento', 'spend', 'valor usado', 'valor usado brl', 'valor usado (brl)'],
        'impressions' => ['impressions', 'impressões', 'impressoes'],
        'reach' => ['reach', 'alcance'],
        'link_clicks' => ['link clicks', 'clicks', 'cliques no link', 'cliques', 'click'],
        'ctr' => ['ctr', 'ctr (all)', 'unique ctr', 'ctr (todos)'],
        'cpc' => ['cpc', 'cpc (all)', 'cost per click', 'cpc (custo por clique no link)'],
        'cpm' => ['cpm', 'custo por mil', 'cost per 1,000 impressions', 'cpm (custo por 1.000 impressões)', 'cpm (custo por 1.000 impressoes)'],
        'results' => ['results', 'leads', 'conversões', 'conversoes', 'conversions', 'purchases', 'resultados'],
    ];

    public const DISPLAY_LABELS = [
        'campaign_name' => 'Campanha',
        'date' => 'Data',
        'amount_spent' => 'Investimento',
        'investimento' => 'Investimento',
        'impressions' => 'Impressões',
        'impressoes' => 'Impressões',
        'reach' => 'Alcance',
        'alcance' => 'Alcance',
        'link_clicks' => 'Cliques',
        'cliques' => 'Cliques',
        'ctr' => 'CTR',
        'cpc' => 'CPC',
        'cpm' => 'CPM',
        'results' => 'Resultados',
        'resultados' => 'Resultados',
        'cpl' => 'CPL',
    ];

    public function availableMonths(?Carbon $earliestDate = null): array
    {
        $today = Carbon::today();
        $end = $today->copy()->startOfMonth();
        if ($earliestDate) {
            $start = $earliestDate->copy()->startOfMonth();
        } else {
            $start = $today->copy()->subMonths(17)->startOfMonth();
        }
        $months = [];
        $cursor = $end->copy();
        while ($cursor->greaterThanOrEqualTo($start)) {
            $months[] = [
                'value' => $cursor->format('Y-m'),
                'label' => $this->monthLabel($cursor),
            ];
            $cursor->subMonth()->startOfMonth();
        }
        return $months;
    }

    public function monthRangesForParam(?string $mesParam): array
    {
        if (!$mesParam) {
            return $this->lastCompleteMonthRanges();
        }
        try {
            $year = (int) substr($mesParam, 0, 4);
            $month = (int) substr($mesParam, 5, 2);
            $currentStart = Carbon::create($year, $month, 1)->startOfDay();
            $currentEnd = $currentStart->copy()->endOfMonth()->endOfDay();
        } catch (\Throwable $ex) {
            return $this->lastCompleteMonthRanges();
        }
        $previousEnd = $currentStart->copy()->subDay()->endOfDay();
        $previousStart = $previousEnd->copy()->startOfMonth()->startOfDay();
        return [
            'current_start' => $currentStart,
            'current_end' => $currentEnd,
            'previous_start' => $previousStart,
            'previous_end' => $previousEnd,
        ];
    }

    public function lastCompleteMonthRanges(?Carbon $referenceDate = null): array
    {
        $reference = $referenceDate ?: Carbon::today();
        $currentMonthStart = $reference->copy()->startOfMonth();
        $currentPeriodEnd = $currentMonthStart->copy()->subDay()->endOfDay();
        $currentPeriodStart = $currentPeriodEnd->copy()->startOfMonth()->startOfDay();
        $previousPeriodEnd = $currentPeriodStart->copy()->subDay()->endOfDay();
        $previousPeriodStart = $previousPeriodEnd->copy()->startOfMonth()->startOfDay();
        return [
            'current_start' => $currentPeriodStart,
            'current_end' => $currentPeriodEnd,
            'previous_start' => $previousPeriodStart,
            'previous_end' => $previousPeriodEnd,
        ];
    }

    public function metricsQuery(?int $empresaId, ?Carbon $dataInicio, ?Carbon $dataFim)
    {
        $query = CampanhaMetric::query()->with(['upload', 'upload.empresa']);
        if ($empresaId) {
            $query->whereHas('upload', fn ($q) => $q->where('empresa_id', $empresaId));
        }
        if ($dataInicio) {
            $query->where('data', '>=', $dataInicio->toDateString());
        }
        if ($dataFim) {
            $query->where('data', '<=', $dataFim->toDateString());
        }
        return $query;
    }

    public function summarizeMetrics(Collection $rows): array
    {
        $investimento = $rows->sum('investimento');
        $impressoes = (int) $rows->sum('impressoes');
        $alcance = (int) $rows->sum('alcance');
        $cliques = (int) $rows->sum('cliques');
        $resultados = $rows->sum('resultados');

        $ctr = $impressoes ? ($cliques / $impressoes) * 100 : 0;
        $cpc = $cliques ? ($investimento / $cliques) : 0;
        $cpm = $impressoes ? ($investimento / $impressoes) * 1000 : 0;
        $cpl = $resultados ? ($investimento / $resultados) : 0;

        return [
            'investimento' => $investimento,
            'impressoes' => $impressoes,
            'alcance' => $alcance,
            'cliques' => $cliques,
            'resultados' => $resultados,
            'ctr' => $ctr,
            'cpc' => $cpc,
            'cpm' => $cpm,
            'cpl' => $cpl,
        ];
    }

    public function campaignTable(Collection $rows): array
    {
        return $rows->groupBy('campanha')
            ->map(function (Collection $group) {
                $investimento = $group->sum('investimento');
                $impressoes = (int) $group->sum('impressoes');
                $alcance = (int) $group->sum('alcance');
                $cliques = (int) $group->sum('cliques');
                $resultados = $group->sum('resultados');
                $ctr = $impressoes ? ($cliques / $impressoes) * 100 : 0;
                $cpc = $cliques ? ($investimento / $cliques) : 0;
                $cpm = $impressoes ? ($investimento / $impressoes) * 1000 : 0;
                $cpl = $resultados ? ($investimento / $resultados) : 0;
                return [
                    'campanha' => $group->first()->campanha,
                    'investimento' => $investimento,
                    'impressoes' => $impressoes,
                    'alcance' => $alcance,
                    'cliques' => $cliques,
                    'ctr' => $ctr,
                    'cpc' => $cpc,
                    'cpm' => $cpm,
                    'resultados' => $resultados,
                    'cpl' => $cpl,
                ];
            })
            ->sortByDesc('investimento')
            ->values()
            ->all();
    }

    public function timelineData(Collection $rows): array
    {
        $grouped = $rows->groupBy(fn ($row) => optional($row->data)->format('Y-m-d') ?? 'Sem data');
        $labels = [];
        $values = [];
        foreach ($grouped as $label => $group) {
            $labels[] = $label;
            $values[] = (float) $group->sum('investimento');
        }
        return ['labels' => $labels, 'values' => $values];
    }

    public function readTable(string $path): Collection
    {
        if (!file_exists($path)) {
            throw new RuntimeException('Arquivo não encontrado.');
        }
        $extension = strtolower(pathinfo($path, PATHINFO_EXTENSION));
        if (in_array($extension, ['xlsx', 'xls'])) {
            $spreadsheet = IOFactory::load($path);
            $sheet = $spreadsheet->getActiveSheet()->toArray(null, true, true, true);
            return collect($this->normalizeSheetRows($sheet));
        }

        $csv = new Csv();
        $csv->setReadDataOnly(true);
        $csv->setDelimiter($this->detectDelimiter($path));
        $spreadsheet = $csv->load($path);
        $sheet = $spreadsheet->getActiveSheet()->toArray(null, true, true, true);
        return collect($this->normalizeSheetRows($sheet));
    }

    public function suggestMapping(array $columns): array
    {
        $normalized = [];
        foreach ($columns as $column) {
            $normalized[$column] = $this->normalizeHeader($column);
        }
        $mapping = [];
        foreach (self::COLUMN_ALIASES as $canonical => $aliases) {
            $candidates = array_map(fn ($alias) => $this->normalizeHeader($alias), $aliases);
            foreach ($normalized as $original => $norm) {
                if (in_array($norm, $candidates, true)) {
                    $mapping[$canonical] = $original;
                    break;
                }
            }
        }
        return $mapping;
    }

    public function importMetricsFromUpload(UploadCampanha $upload, array $manualMapping = []): array
    {
        $path = Storage::path($upload->arquivo);
        $rows = $this->readTable($path);
        if ($rows->isEmpty()) {
            return [
                'imported_count' => 0,
                'duplicate_in_file_count' => 0,
                'duplicate_existing_count' => 0,
                'mapping' => [],
                'warnings' => ['Arquivo vazio.'],
                'missing_required' => ['campaign_name'],
                'detected_columns' => [],
            ];
        }

        $columns = array_keys($rows->first());
        $mapping = $this->suggestMapping($columns);
        foreach ($manualMapping as $key => $value) {
            if ($value) {
                $mapping[$key] = $value;
            }
        }

        $missingRequired = [];
        if (!isset($mapping['campaign_name'])) {
            $missingRequired[] = 'campaign_name';
        }
        if ($missingRequired) {
            return [
                'imported_count' => 0,
                'duplicate_in_file_count' => 0,
                'duplicate_existing_count' => 0,
                'mapping' => $mapping,
                'warnings' => [],
                'missing_required' => $missingRequired,
                'detected_columns' => $columns,
            ];
        }

        $upload->metricas()->delete();
        $existingFingerprints = CampanhaMetric::query()
            ->whereHas('upload', fn ($q) => $q->where('empresa_id', $upload->empresa_id))
            ->where('upload_id', '!=', $upload->id)
            ->where('fingerprint', '!=', '')
            ->pluck('fingerprint')
            ->all();
        $existingFingerprints = array_flip($existingFingerprints);

        $batch = [];
        $warnings = [];
        $duplicateInFile = 0;
        $duplicateExisting = 0;
        $seenInFile = [];

        foreach ($rows as $row) {
            $campaignName = trim((string) ($row[$mapping['campaign_name']] ?? ''));
            if ($campaignName === '') {
                continue;
            }
            $investimento = $this->parseDecimal($row[$mapping['amount_spent']] ?? null);
            $impressoes = (int) $this->parseDecimal($row[$mapping['impressions']] ?? null);
            $alcance = (int) $this->parseDecimal($row[$mapping['reach']] ?? null);
            $cliques = (int) $this->parseDecimal($row[$mapping['link_clicks']] ?? null);
            $resultados = $this->parseDecimal($row[$mapping['results']] ?? null);
            $ctr = $this->parseDecimal($row[$mapping['ctr']] ?? null);
            $cpc = $this->parseDecimal($row[$mapping['cpc']] ?? null);
            $cpm = $this->parseDecimal($row[$mapping['cpm']] ?? null);
            $data = $this->parseDate($row[$mapping['date']] ?? null) ?? $upload->data_inicio;

            if ($ctr == 0 && $impressoes) {
                $ctr = ($cliques / $impressoes) * 100;
            }
            if ($cpc == 0 && $cliques) {
                $cpc = $investimento / $cliques;
            }
            if ($cpm == 0 && $impressoes) {
                $cpm = ($investimento / $impressoes) * 1000;
            }
            $cpl = $resultados ? ($investimento / $resultados) : 0;

            $fingerprint = $this->metricFingerprint(
                $upload->empresa_id,
                $data,
                $campaignName,
                $investimento,
                $impressoes,
                $alcance,
                $cliques,
                $ctr,
                $cpc,
                $cpm,
                $resultados
            );
            if (isset($seenInFile[$fingerprint])) {
                $duplicateInFile++;
                continue;
            }
            if (isset($existingFingerprints[$fingerprint])) {
                $duplicateExisting++;
                continue;
            }
            $seenInFile[$fingerprint] = true;

            $batch[] = [
                'upload_id' => $upload->id,
                'fingerprint' => $fingerprint,
                'data' => $data,
                'campanha' => mb_substr($campaignName, 0, 255),
                'investimento' => $investimento,
                'impressoes' => $impressoes,
                'alcance' => $alcance,
                'cliques' => $cliques,
                'ctr' => $ctr,
                'cpc' => $cpc,
                'cpm' => $cpm,
                'resultados' => $resultados,
                'cpl' => $cpl,
                'created_at' => now(),
                'updated_at' => now(),
            ];
        }

        if ($batch) {
            CampanhaMetric::insert($batch);
        }
        if (!isset($mapping['date']) && !$upload->data_inicio) {
            $warnings[] = 'Arquivo sem coluna de data; use o período manual para análises temporais mais precisas.';
        }
        if ($duplicateInFile) {
            $warnings[] = sprintf('%d linha(s) duplicada(s) no mesmo arquivo foram ignoradas.', $duplicateInFile);
        }
        if ($duplicateExisting) {
            $warnings[] = sprintf('%d linha(s) já existentes em uploads anteriores da empresa foram ignoradas.', $duplicateExisting);
        }

        return [
            'imported_count' => count($batch),
            'duplicate_in_file_count' => $duplicateInFile,
            'duplicate_existing_count' => $duplicateExisting,
            'mapping' => $mapping,
            'warnings' => $warnings,
            'missing_required' => [],
            'detected_columns' => $columns,
        ];
    }

    public function inferUploadPeriodFromDataframe(Collection $rows, array $configMapping = [], array $detectedMapping = []): array
    {
        $startColumn = $configMapping['inicio_relatorio'] ?? null;
        $endColumn = $configMapping['fim_relatorio'] ?? null;
        $dateColumn = $configMapping['date'] ?? ($detectedMapping['date'] ?? null);

        $startDate = $startColumn ? $this->inferDateFromColumn($rows, $startColumn, 'min') : null;
        $endDate = $endColumn ? $this->inferDateFromColumn($rows, $endColumn, 'max') : null;

        if ($dateColumn) {
            if ($startDate === null) {
                $startDate = $this->inferDateFromColumn($rows, $dateColumn, 'min');
            }
            if ($endDate === null) {
                $endDate = $this->inferDateFromColumn($rows, $dateColumn, 'max');
            }
        }

        if ($startDate && !$endDate) {
            $endDate = $startDate;
        }
        if ($endDate && !$startDate) {
            $startDate = $endDate;
        }

        return [$startDate, $endDate, $this->inferPeriodType($startDate, $endDate)];
    }

    public function inferPeriodType(?Carbon $startDate, ?Carbon $endDate): string
    {
        if (!$startDate || !$endDate) {
            return 'personalizado';
        }
        if ($startDate->year === $endDate->year && $startDate->month === $endDate->month) {
            if ($startDate->day === 1 && $endDate->day === $endDate->copy()->endOfMonth()->day) {
                return 'mensal';
            }
        }
        if ($startDate->year === $endDate->year && $startDate->month === 1 && $startDate->day === 1 && $endDate->month === 12 && $endDate->day === 31) {
            return 'anual';
        }
        if ($endDate->diffInDays($startDate) <= 7) {
            return 'semanal';
        }
        return 'personalizado';
    }

    public function metricFingerprint($empresaId, $data, $campanha, $investimento, $impressoes, $alcance, $cliques, $ctr, $cpc, $cpm, $resultados): string
    {
        $payload = implode('|', [
            $empresaId,
            $data ? Carbon::parse($data)->toDateString() : '',
            mb_strtolower(trim($campanha)),
            $investimento,
            $impressoes,
            $alcance,
            $cliques,
            $ctr,
            $cpc,
            $cpm,
            $resultados,
        ]);
        return hash('sha256', $payload);
    }

    private function normalizeHeader($value): string
    {
        return trim(preg_replace('/\s+/', ' ', strtolower(preg_replace('/[^a-zA-Z0-9]+/', ' ', (string) $value))));
    }

    private function parseDecimal($value): float
    {
        if ($value === null) {
            return 0;
        }
        if (is_numeric($value)) {
            return (float) $value;
        }
        $text = trim((string) $value);
        if ($text === '') {
            return 0;
        }
        $text = str_replace(['%', 'R$', ' '], '', $text);
        if (str_contains($text, ',') && str_contains($text, '.')) {
            if (strrpos($text, ',') > strrpos($text, '.')) {
                $text = str_replace('.', '', $text);
                $text = str_replace(',', '.', $text);
            } else {
                $text = str_replace(',', '', $text);
            }
        } elseif (str_contains($text, ',')) {
            $text = str_replace('.', '', $text);
            $text = str_replace(',', '.', $text);
        }
        return (float) $text;
    }

    private function parseDate($value): ?Carbon
    {
        if (!$value) {
            return null;
        }
        $text = trim((string) $value);
        if ($text === '') {
            return null;
        }
        try {
            return Carbon::parse($text);
        } catch (\Throwable $ex) {
            return null;
        }
    }

    private function inferDateFromColumn(Collection $rows, string $column, string $pick): ?Carbon
    {
        $parsed = [];
        foreach ($rows as $row) {
            if (!array_key_exists($column, $row)) {
                continue;
            }
            $value = $this->parseDate($row[$column]);
            if ($value) {
                $parsed[] = $value;
            }
        }
        if (!$parsed) {
            return null;
        }
        usort($parsed, fn ($a, $b) => $a <=> $b);
        return $pick === 'min' ? $parsed[0] : $parsed[count($parsed) - 1];
    }

    private function normalizeSheetRows(array $rows): array
    {
        if (!$rows) {
            return [];
        }
        $headerRow = array_shift($rows);
        $headers = [];
        foreach ($headerRow as $cell) {
            $headers[] = trim((string) $cell);
        }
        $normalized = [];
        foreach ($rows as $row) {
            $entry = [];
            foreach ($headers as $index => $header) {
                $cellKey = chr(ord('A') + $index);
                $entry[$header] = $row[$cellKey] ?? null;
            }
            $normalized[] = $entry;
        }
        return array_values(array_filter($normalized, fn ($item) => array_filter($item, fn ($value) => $value !== null && $value !== '')));
    }

    private function detectDelimiter(string $path): string
    {
        $sample = file_get_contents($path, false, null, 0, 4096);
        $delimiters = [',', ';', "\t", '|'];
        $best = ',';
        $max = 0;
        foreach ($delimiters as $delimiter) {
            $count = substr_count($sample, $delimiter);
            if ($count > $max) {
                $max = $count;
                $best = $delimiter;
            }
        }
        return $best;
    }

    private function monthLabel(Carbon $date): string
    {
        $map = [
            1 => 'Janeiro', 2 => 'Fevereiro', 3 => 'Março', 4 => 'Abril',
            5 => 'Maio', 6 => 'Junho', 7 => 'Julho', 8 => 'Agosto',
            9 => 'Setembro', 10 => 'Outubro', 11 => 'Novembro', 12 => 'Dezembro',
        ];
        return ($map[$date->month] ?? $date->format('m')) . ' ' . $date->year;
    }
}
