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
        Schema::create('empresas', function (Blueprint $table) {
            $table->id();
            $table->string('nome');
            $table->string('cnpj', 18)->default('');
            $table->string('segmento')->default('');
            $table->json('redes_sociais_json')->nullable();
            $table->string('instagram_profile_url')->default('');
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
            $table->boolean('ativo')->default(true);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('empresas');
    }
};
