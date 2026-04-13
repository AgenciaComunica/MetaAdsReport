<?php

use App\Http\Controllers\CampanhaController;
use App\Http\Controllers\ConcorrenteController;
use App\Http\Controllers\EmpresaController;
use App\Http\Controllers\RelatorioController;
use Illuminate\Support\Facades\Route;

// Home
Route::get('/', fn () => redirect()->route('campanhas.dashboard'))->name('home');

// Empresas
Route::prefix('empresas')->name('empresas.')->group(function () {
    Route::get('/', [EmpresaController::class, 'index'])->name('list');
    Route::get('/nova', [EmpresaController::class, 'create'])->name('create');
    Route::post('/nova', [EmpresaController::class, 'store'])->name('store');
    Route::get('/{empresa}', [EmpresaController::class, 'show'])->name('detail');
    Route::get('/{empresa}/editar', [EmpresaController::class, 'edit'])->name('update');
    Route::put('/{empresa}/editar', [EmpresaController::class, 'update'])->name('update.put');
    Route::delete('/{empresa}/excluir', [EmpresaController::class, 'destroy'])->name('delete');
    Route::post('/{empresa}/usuarios', [EmpresaController::class, 'userStore'])->name('user_store');
    Route::post('/{empresa}/uploads/adicionar', [EmpresaController::class, 'uploadConfigCreate'])->name('upload_config_create');
    Route::get('/{empresa}/uploads/{config}/configurar', [EmpresaController::class, 'uploadConfigEdit'])->name('upload_config_update');
    Route::put('/{empresa}/uploads/{config}/configurar', [EmpresaController::class, 'uploadConfigUpdate'])->name('upload_config_update.put');
    Route::delete('/{empresa}/uploads/{config}/excluir', [EmpresaController::class, 'uploadConfigDelete'])->name('upload_config_delete');
});

// Campanhas
Route::prefix('campanhas')->name('campanhas.')->group(function () {
    Route::get('/', [CampanhaController::class, 'dashboard'])->name('dashboard');
    Route::get('/uploads', [CampanhaController::class, 'uploadList'])->name('upload_list');
    Route::get('/uploads/novo', [CampanhaController::class, 'uploadCreate'])->name('upload_create');
    Route::post('/uploads/novo', [CampanhaController::class, 'uploadStore'])->name('upload_store');
    Route::get('/uploads/{upload}', [CampanhaController::class, 'uploadDetail'])->name('upload_detail');
    Route::delete('/uploads/{upload}/excluir', [CampanhaController::class, 'uploadDelete'])->name('upload_delete');
    Route::delete('/uploads/{upload}/campanhas/excluir', [CampanhaController::class, 'uploadCampaignDelete'])->name('upload_campaign_delete');
    Route::delete('/painel-uploads/{upload}/excluir', [CampanhaController::class, 'panelUploadDelete'])->name('panel_upload_delete');
    Route::delete('/eventos-painel/{evento}/excluir', [CampanhaController::class, 'eventoPainelDelete'])->name('evento_painel_delete');
    Route::get('/eventos-painel/template', [CampanhaController::class, 'eventoPainelTemplateDownload'])->name('evento_painel_template_download');
    Route::get('/uploads/{upload}/mapeamento', [CampanhaController::class, 'manualMapping'])->name('manual_mapping');
    Route::post('/uploads/{upload}/mapeamento', [CampanhaController::class, 'manualMappingStore'])->name('manual_mapping.store');
});

// Concorrentes
Route::prefix('concorrentes')->name('concorrentes.')->group(function () {
    Route::get('/', [ConcorrenteController::class, 'index'])->name('list');
    Route::get('/novo', [ConcorrenteController::class, 'create'])->name('create');
    Route::post('/novo', [ConcorrenteController::class, 'store'])->name('store');
    Route::get('/importar', [ConcorrenteController::class, 'import'])->name('import');
    Route::post('/importar', [ConcorrenteController::class, 'importStore'])->name('import.store');
    Route::get('/instagram', [ConcorrenteController::class, 'instagramImport'])->name('instagram_import');
    Route::post('/instagram', [ConcorrenteController::class, 'instagramImportStore'])->name('instagram_import.store');
    Route::get('/{concorrente}/editar', [ConcorrenteController::class, 'edit'])->name('update');
    Route::put('/{concorrente}/editar', [ConcorrenteController::class, 'update'])->name('update.put');
    Route::delete('/{concorrente}/excluir', [ConcorrenteController::class, 'destroy'])->name('delete');
    Route::post('/avaliar-agora', [ConcorrenteController::class, 'avaliarAgora'])->name('evaluate_now');
});

// Relatórios
Route::prefix('relatorios')->name('relatorios.')->group(function () {
    Route::get('/', [RelatorioController::class, 'index'])->name('list');
    Route::post('/gerar', [RelatorioController::class, 'generate'])->name('generate');
    Route::get('/{relatorio}', [RelatorioController::class, 'show'])->name('detail');
    Route::get('/{relatorio}/html', [RelatorioController::class, 'htmlExport'])->name('html_export');
    Route::delete('/{relatorio}/excluir', [RelatorioController::class, 'destroy'])->name('delete');
});
