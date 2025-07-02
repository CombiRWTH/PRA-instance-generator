"""
URL configuration for website project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    ## for generation
    # start page
    path('start/', views.start, name='start'),
    path('next-mode/', views.start, name='next-mode'), # the views.start is irrelevent, as this path will be catched by the middleware
    # the different modes (independent or not)
    path('wardtyp/', views.wardtyp, name='wardtyp'), # this is the version, where los and age are chosen together
    path('los/', views.los, name='los'),
    path('age/', views.age, name='age'),
    # rest settings (equal for both modes)
    path('lor/', views.lor, name='lor'),
    path('rateparams/', views.rateparams, name='rateparams'),
    path('rooms/', views.rooms, name='rooms'),
    path('confirm/', views.confirm, name='confirm'),
    path('generate/', views.generate, name='generate'),
    # process stuff (while generation)
    path('loading/', views.loading, name='loading'),
    path('progress/', views.progress, name='progress'),
    path('abort/', views.abort, name='abort'),
    ## general
    path('', views.index, name='index'),
    # for displaying the instances/templates
    path('instances/', views.instances, name='instances'),
    path('templates/', views.templates, name='templates'),
    path('delete/', views.delete, name='delete'),
]
