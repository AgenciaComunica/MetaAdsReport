from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from empresas.models import Empresa
from ia.models import AnaliseConcorrencial
from ia.services import save_competitor_analysis

from .forms import ConcorrenteAdForm, ConcorrenteImportForm, InstagramProfileImportForm
from .models import ConcorrenteAd
from .services import (
    competitor_profiles,
    competitor_summary_for_name_in_period,
    facebook_ads_library_session,
    import_competitor_file,
    import_instagram_profile,
    refresh_instagram_profile_record,
)


def concorrente_list(request):
    queryset = ConcorrenteAd.objects.select_related('empresa')
    empresa_id = request.session.get('active_company_id')
    empresa = Empresa.objects.filter(pk=empresa_id).first() if empresa_id else None
    competitor_status_map = {item['nome']: item for item in competitor_profiles(queryset)}
    analyses = AnaliseConcorrencial.objects.exclude(concorrente_nome='')
    analysis_map = {
        (analysis.empresa_id, analysis.concorrente_nome): analysis
        for analysis in analyses
    }
    ads = list(queryset[:300])
    for ad in ads:
        profile = competitor_status_map.get(ad.concorrente_nome.strip())
        ad.activity_label = profile['activity_label'] if profile else 'Sem Avaliação Feita'
        ad.activity_class = profile['activity_class'] if profile else 'is-none'
        ad.analysis = analysis_map.get((ad.empresa_id, ad.concorrente_nome))
        ad.has_analysis = ad.analysis is not None
        if ad.has_analysis and ad.activity_label == 'Sem Avaliação Feita':
            ad.activity_label = 'Sem Ads'
    return render(
        request,
        'concorrentes/list.html',
        {
            'ads': ads,
            'empresa': empresa,
            'competitor_profiles': list(competitor_status_map.values()),
        },
    )


def concorrente_create(request):
    messages.info(request, 'O cadastro manual foi removido. Use Perfil Instagram ou Importar arquivo.')
    return redirect('concorrentes:list')


def concorrente_import(request):
    form = ConcorrenteImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        empresa = form.cleaned_data['empresa']
        uploaded_file = form.cleaned_data['arquivo']
        imported_file_path = uploaded_file.temporary_file_path() if hasattr(uploaded_file, 'temporary_file_path') else None
        if not imported_file_path:
            from django.core.files.storage import default_storage

            temp_path = default_storage.save(f'tmp/{uploaded_file.name}', uploaded_file)
            imported_file_path = default_storage.path(temp_path)
        total = import_competitor_file(empresa, imported_file_path)
        messages.success(request, f'{total} anúncios concorrentes importados.')
        return redirect('concorrentes:list')
    return render(request, 'concorrentes/import_form.html', {'form': form})


def concorrente_instagram_import(request):
    form = InstagramProfileImportForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        empresa = form.cleaned_data['empresa']
        profile_url = form.cleaned_data['instagram_profile_url']
        ad, warnings = import_instagram_profile(empresa, profile_url)
        messages.success(request, f'Perfil @{ad.concorrente_nome} importado com sucesso.')
        for warning in warnings:
            messages.warning(request, warning)
        return redirect('concorrentes:list')
    return render(request, 'concorrentes/instagram_import_form.html', {'form': form})


def concorrente_avaliar_agora(request):
    empresa_id = request.POST.get('empresa') or request.GET.get('empresa') or request.session.get('active_company_id')
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    period_start = parse_date(request.POST.get('data_inicio') or request.GET.get('data_inicio') or '')
    period_end = parse_date(request.POST.get('data_fim') or request.GET.get('data_fim') or '')
    queryset = ConcorrenteAd.objects.filter(empresa=empresa)
    profiles = competitor_profiles(queryset)
    if not profiles:
        messages.error(request, 'Cadastre ao menos um concorrente antes de rodar a análise.')
        return redirect('concorrentes:list')

    refresh_warnings = []
    ads_session = facebook_ads_library_session()
    for ad in queryset.filter(categoria='Perfil importado').exclude(link=''):
        try:
            refreshed_ad, warnings = refresh_instagram_profile_record(ad, ads_session=ads_session)
            refresh_warnings.extend([f'{refreshed_ad.concorrente_nome}: {warning}' for warning in warnings])
        except Exception:
            refresh_warnings.append(f'{ad.concorrente_nome}: nao foi possivel atualizar os dados publicos do perfil agora.')

    queryset = ConcorrenteAd.objects.filter(empresa=empresa)
    profiles = competitor_profiles(queryset)
    analysis_count = 0
    total_ads = 0
    for profile in profiles:
        summary = competitor_summary_for_name_in_period(queryset, profile['nome'], period_start, period_end)
        analysis = save_competitor_analysis(empresa, profile['nome'], summary)
        analysis_count += 1
        total_ads += analysis.total_anuncios
    messages.success(
        request,
        f'Análises atualizadas para {empresa.nome}. {analysis_count} concorrente(s) processado(s) com base em {total_ads} anúncio(s) observável(is).',
    )
    for warning in refresh_warnings:
        messages.warning(request, warning)
    return redirect('campanhas:dashboard')
