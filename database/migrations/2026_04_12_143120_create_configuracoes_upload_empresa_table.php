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
        Schema::create('configuracoes_upload_empresa', function (Blueprint $table) {
            $table->id();
            $table->foreignId('empresa_id')->constrained('empresas')->cascadeOnDelete();
            $table->string('nome');
            $table->string('tipo_documento', 40)->default('');
            $table->string('arquivo_exemplo')->default('');
            $table->string('nome_arquivo_exemplo')->default('');
            $table->json('colunas_detectadas_json')->nullable();
            $table->json('preview_json')->nullable();
            $table->json('mapeamento_json')->nullable();
            $table->json('campos_principais_json')->nullable();
            $table->json('metricas_painel_json')->nullable();
            $table->json('configuracao_analise_json')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('configuracoes_upload_empresa');
    }
};
