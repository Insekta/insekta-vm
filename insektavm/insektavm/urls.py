"""insektavm URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.conf.urls import url, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.urls import path, include
from django.contrib import admin

from insektavm.vm import apiurls as vm_apiurls
from insektavm.vpn import apiurls as vpn_apiurls


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/1.0/vm/', include(vm_apiurls)),
    path('api/1.0/vpn/', include(vpn_apiurls))
]
