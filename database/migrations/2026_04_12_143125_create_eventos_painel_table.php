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
        Schema::create('eventos_painel', function (Blueprint $table) {
            $table->id();
            $table->foreignId('configuracao_id')->constrained('configuracoes_upload_empresa')->cascadeOnDelete();
            $table->string('nome_evento');
            $table->date('data_evento');
            $table->string('impacto', 10);
            $table->unsignedInteger('leads_media')->default(0);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('eventos_painel');
    }
};
