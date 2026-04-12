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
        Schema::create('uploads_painel', function (Blueprint $table) {
            $table->id();
            $table->foreignId('configuracao_id')->constrained('configuracoes_upload_empresa')->cascadeOnDelete();
            $table->string('arquivo');
            $table->string('tipo_upload', 20)->default('');
            $table->string('nome_arquivo');
            $table->json('colunas_detectadas_json')->nullable();
            $table->json('preview_json')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('uploads_painel');
    }
};
