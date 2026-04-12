<?php

use Carbon\CarbonInterface;

if (! function_exists('br_number')) {
    function br_number(mixed $value, ?int $decimals = null): string
    {
        if ($value === null || $value === '') {
            return '0';
        }

        if (! is_numeric($value)) {
            return (string) $value;
        }

        $number = (float) $value;
        $precision = $decimals;

        if ($precision === null) {
            $precision = floor($number) === $number ? 0 : 2;
        }

        $formatted = number_format($number, $precision, ',', '.');

        if ($precision > 0) {
            $formatted = rtrim(rtrim($formatted, '0'), ',');
        }

        return $formatted;
    }
}

if (! function_exists('br_currency')) {
    function br_currency(mixed $value): string
    {
        return 'R$ '.br_number($value, 2);
    }
}

if (! function_exists('br_date')) {
    function br_date(mixed $value, string $format = 'd/m/Y'): string
    {
        if (! $value) {
            return '-';
        }

        if ($value instanceof CarbonInterface) {
            return $value->format($format);
        }

        try {
            return \Carbon\Carbon::parse((string) $value)->format($format);
        } catch (\Throwable) {
            return (string) $value;
        }
    }
}

if (! function_exists('br_datetime')) {
    function br_datetime(mixed $value): string
    {
        return br_date($value, 'd/m/Y H:i');
    }
}
