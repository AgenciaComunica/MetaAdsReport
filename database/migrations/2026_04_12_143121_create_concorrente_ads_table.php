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
        Schema::create('concorrente_ads', function (Blueprint $table) {
            $table->id();
            $table->foreignId('empresa_id')->constrained('empresas')->cascadeOnDelete();
            $table->string('concorrente_nome');
            $table->text('texto_principal')->nullable();
            $table->string('titulo')->default('');
            $table->text('descricao')->nullable();
            $table->string('cta', 100)->default('');
            $table->string('plataforma', 100)->default('Meta Ads');
            $table->string('link')->default('');
            $table->date('data_referencia')->nullable();
            $table->string('categoria', 100)->default('');
            $table->boolean('ads_biblioteca_ativo')->default(false);
            $table->string('ads_biblioteca_query')->default('');
            $table->unsignedInteger('ads_biblioteca_sinal')->default(0);
            $table->timestamp('ads_biblioteca_consultado_em')->nullable();
            $table->unsignedInteger('seguidores')->default(0);
            $table->unsignedInteger('posts_total_publicos')->default(0);
            $table->unsignedInteger('feed_posts_visiveis')->default(0);
            $table->json('feed_posts_detalhes')->nullable();
            $table->json('feed_datas_publicadas')->nullable();
            $table->string('feed_cadencia', 100)->default('');
            $table->json('feed_formatos')->nullable();
            $table->text('observacoes')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('concorrente_ads');
    }
};
