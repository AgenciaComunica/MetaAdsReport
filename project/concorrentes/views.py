from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.urls import reverse

from empresas.services import refresh_empresa_profile_record
from empresas.models import Empresa
from ia.models import AnaliseConcorrencial
from ia.services import save_competitor_analysis

from .forms import ConcorrenteAdForm, ConcorrenteImportForm, ConcorrentePerfilForm, InstagramProfileImportForm
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
    query = {}
    empresa_id = request.GET.get('empresa') or request.session.get('active_company_id')
    if empresa_id:
        query['empresa'] = empresa_id
    query['tab'] = 'concorrentes'
    return redirect(f"{reverse('campanhas:dashboard')}?{urlencode(query)}")


def concorrente_create(request):
    return redirect('concorrentes:instagram_import')


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


def concorrente_update(request, pk):
    concorrente = get_object_or_404(ConcorrenteAd.objects.select_related('empresa'), pk=pk)
    nome_anterior = concorrente.concorrente_nome
    form = ConcorrentePerfilForm(request.POST or None, instance=concorrente)
    if request.method == 'POST' and form.is_valid():
        concorrente = form.save(commit=False)
        concorrente.categoria = 'Perfil importado'
        concorrente.plataforma = 'Instagram / Meta Ads'
        concorrente.save()
        if nome_anterior.strip().lower() != concorrente.concorrente_nome.strip().lower():
            AnaliseConcorrencial.objects.filter(
                empresa=concorrente.empresa,
                concorrente_nome__iexact=nome_anterior,
            ).delete()
        if concorrente.link:
            try:
                refresh_instagram_profile_record(concorrente)
            except Exception:
                messages.warning(request, 'Concorrente salvo, mas nao foi possivel atualizar os dados publicos agora.')
        messages.success(request, 'Concorrente atualizado com sucesso.')
        return redirect('concorrentes:list')
    return render(
        request,
        'concorrentes/profile_form.html',
        {'form': form, 'title': 'Editar Concorrente', 'concorrente': concorrente},
    )


def concorrente_delete(request, pk):
    concorrente = get_object_or_404(ConcorrenteAd.objects.select_related('empresa'), pk=pk)
    if request.method == 'POST':
        nome = concorrente.concorrente_nome
        AnaliseConcorrencial.objects.filter(
            empresa=concorrente.empresa,
            concorrente_nome__iexact=nome,
        ).delete()
        concorrente.delete()
        messages.success(request, f'Concorrente "{nome}" removido com sucesso.')
        return redirect('concorrentes:list')
    return render(request, 'concorrentes/confirm_delete.html', {'concorrente': concorrente})


def concorrente_avaliar_agora(request):
    empresa_id = request.POST.get('empresa') or request.GET.get('empresa') or request.session.get('active_company_id')
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    period_start = parse_date(request.POST.get('data_inicio') or request.GET.get('data_inicio') or '')
    period_end = parse_date(request.POST.get('data_fim') or request.GET.get('data_fim') or '')
    previous_start_raw = request.POST.get('data_inicio_anterior') or request.GET.get('data_inicio_anterior') or ''
    previous_end_raw = request.POST.get('data_fim_anterior') or request.GET.get('data_fim_anterior') or ''
    queryset = ConcorrenteAd.objects.filter(empresa=empresa)
    profiles = competitor_profiles(queryset)
    if not profiles:
        messages.error(request, 'Cadastre ao menos um concorrente antes de rodar a análise.')
        return redirect('concorrentes:list')

    refresh_warnings = []
    ads_session = facebook_ads_library_session()
    if empresa.instagram_profile_url:
        try:
            _, empresa_warnings = refresh_empresa_profile_record(empresa, ads_session=ads_session)
            refresh_warnings.extend([f'Empresa {empresa.nome}: {warning}' for warning in empresa_warnings])
        except Exception:
            refresh_warnings.append(f'Empresa {empresa.nome}: nao foi possivel atualizar os dados publicos do perfil agora.')
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
    company_summary = None
    if empresa.instagram_profile_url:
        from empresas.services import empresa_digital_summary

        company_summary = empresa_digital_summary(empresa, period_start, period_end)
    for profile in profiles:
        summary = competitor_summary_for_name_in_period(queryset, profile['nome'], period_start, period_end)
        analysis = save_competitor_analysis(empresa, profile['nome'], summary, company_payload=company_summary)
        analysis_count += 1
        total_ads += analysis.total_anuncios
    messages.success(
        request,
        f'Análises atualizadas para {empresa.nome}. {analysis_count} concorrente(s) processado(s) com base em {total_ads} anúncio(s) observável(is).',
    )
    for warning in refresh_warnings:
        messages.warning(request, warning)
    query_string = urlencode(
        {
            'empresa': empresa.id,
            'data_inicio': period_start.isoformat() if period_start else '',
            'data_fim': period_end.isoformat() if period_end else '',
            'data_inicio_anterior': previous_start_raw,
            'data_fim_anterior': previous_end_raw,
        }
    )
    return redirect(f'{reverse("campanhas:dashboard")}?{query_string}#analise-digital')
