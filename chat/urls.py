from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # UI 路由
    path('ui/<int:application_id>/', 
         views.ChatWidgetView.as_view(), 
         name='chat_widget'),
    
    # 设计页面路由
    path('design/', 
         views.DesignView.as_view(), 
         name='design_page'),
    
    # 应用相关
    path('applications/<int:application_id>/', 
         views.ApplicationDetailView.as_view(), 
         name='application_detail'),
    path('applications/', 
         views.ApplicationListView.as_view(), 
         name='application_list'),
    
    # 对话相关
    path('applications/<int:application_id>/conversations/', 
         views.ConversationListView.as_view(), 
         name='conversation_list'),
    path('applications/<int:application_id>/conversations/<str:conversation_id>/', 
         views.ConversationDetailView.as_view(), 
         name='conversation_detail'),
    
    # 消息相关
    path('applications/<int:application_id>/conversations/<str:conversation_id>/messages/', 
         views.MessageListView.as_view(), 
         name='message_list'),
    path('applications/<int:application_id>/conversations/<str:conversation_id>/messages/stream/', 
         views.MessageStreamView.as_view(), 
         name='message_stream'),
]