<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('campanha_metrics', function (Blueprint $table) {
            $table->id();
            $table->foreignId('upload_id')->constrained('uploads_campanha')->cascadeOnDelete();
            $table->string('fingerprint', 64)->default('')->index();
            $table->date('data')->nullable();
            $table->string('campanha');
            $table->decimal('investimento', 14, 2)->default(0);
            $table->bigInteger('impressoes')->default(0);
            $table->bigInteger('alcance')->default(0);
            $table->bigInteger('cliques')->default(0);
            $table->decimal('ctr', 8, 4)->default(0);
            $table->decimal('cpc', 12, 4)->default(0);
            $table->decimal('cpm', 12, 4)->default(0);
            $table->decimal('resultados', 14, 2)->default(0);
            $table->decimal('cpl', 12, 4)->default(0);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('campanha_metrics');
    }
};
