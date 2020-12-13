#!/usr/bin/env python

import yaml
import sys
import json
import requests
import base64
from grafana_api.grafana_face import GrafanaFace

if (len(sys.argv) != 4):
  print('Usage: '+sys.argv[0]+' <Grafana URL> <admin password> <configuration filename>')
  exit()

#GLOBAL VARIABLES
file = open('config.yaml')
dashboard_config = yaml.safe_load(file.read())
file.close()
GRAFANA_URL=sys.argv[1]
password=sys.argv[2]
users_passwords={}
config_file=sys.argv[3]
username = dashboard_config['username']
language = dashboard_config['language']
num_panel_per_row = dashboard_config['overview_dashboards']['num_panel_per_row']
h_panel = dashboard_config['overview_dashboards']['panel_height']
w_panel = dashboard_config['overview_dashboards']['panel_weight']
panel_type = dashboard_config['overview_dashboards']['panel_type']
grafana_api = GrafanaFace(auth=(username,password),host=GRAFANA_URL)
file = open('device_dashboard.json')
device_dashboard_template_json = file.read()
file.close()
file = open('overview_dashboard.json')
folder_dashboard_template_json = file.read()
file.close()
file = open('device_panel.json')
device_panel_template_json = file.read()
file.close()

#TODO - Hacer script idempotente
#Borrar elementos?? creo que no

def strToBase64(text):
  return base64.b64encode((text).encode('ascii')).decode('ascii')

def post(URL,DATA,HEADERS):
  try:
    response = requests.post(url=URL, data=DATA,headers=HEADERS)
    return response.content

  except requests.exceptions.RequestException as e:  # This is the correct syntax
    raise SystemExit(e)
    
def put(URL,DATA,HEADERS):
  try:
    response = requests.put(url=URL, data=DATA,headers=HEADERS)
    return response.content

  except requests.exceptions.RequestException as e:  # This is the correct syntax
    raise SystemExit(e)

def get_user_password(login, info=None):
  if info: 
    password = info.get('password',strToBase64(login));
    users_passwords[login] = password; 
  else: 
    password = users_passwords[login]
  
  return password;
  
def update_org_preferences(update):
  URL  = 'http://'+GRAFANA_URL+'/api/org/preferences'
  HEADERS = {'Authorization': 'Basic '+base64.b64encode(('admin:'+password).encode('ascii')).decode('ascii'), 'Content-type': 'application/json'}
  return put(URL,json.dumps(update),HEADERS)

def update_user_preferences(login, update):
  URL  = 'http://'+GRAFANA_URL+'/api/user/preferences'
  HEADERS = {'Authorization': 'Basic '+base64.b64encode((login+':'+get_user_password(login)).encode('ascii')).decode('ascii'), 'Content-type': 'application/json'}
  return put(URL,json.dumps(update),HEADERS)

def get_folder(title):
  folders=grafana_api.search.search_dashboards(query=title, type_='dash-folder')
  return next((item for item in folders if item['title'] == title), None)
  
def createFolder(title):
  folder = get_folder(title)
  if not folder:
      folder=grafana_api.folder.create_folder(title)
  return folder
  
def updateFolderPermissions(title, permissions):
  folder_uid = get_folder(title)['uid']
  grafana_api.folder.update_folder_permissions(folder_uid, permissions)

def createTeam(name):
  team=grafana_api.teams.get_team_by_name(name)
  if (len(team)==0):
    team=grafana_api.teams.add_team({'name':name})
    teamId=team['teamId']
  else:
    teamId=team[0]['id']
  return teamId

def addTeamToFolder(team_name, folder_uid, role):
  if role=='Viewer':
    permission = 1
  elif role=='Editor':
    permission = 2
  
  team_id = grafana_api.teams.get_team_by_name(team_name)[0]['id']
  items = grafana_api.folder.get_folder_permissions(folder_uid)
  #Add team if not present in the folder permission
  if not next((item for item in items if item['teamId'] == team_id), None):
    items.append({'teamId': team_id, 'permission': permission, "permissionName": role})
    permissions = {'items': items}
    return grafana_api.folder.update_folder_permissions(folder_uid, permissions)
  else:
    return {'message': 'Team already present'}
  
def createUser(user_data):
  user=grafana_api.users.search_users(query=user_data['login'])
  if not user:
      user=grafana_api.admin.create_user(user_data)
  else:
      user=user[0]
  return user['id']
  
def addUserToTeam(user_login, team_name):
  user_id=grafana_api.users.search_users(query=user_login)[0]['id']
  team_id=grafana_api.teams.get_team_by_name(team_name)[0]['id']
  members=grafana_api.teams.get_team_members(team_id)
  if not next((item for item in members if item['login'] == user_login), None):
    grafana_api.teams.add_team_member(team_id, user_id)

def get_dashboard(folder_title, dashboard_title):
  dashboards=grafana_api.search.search_dashboards(query=dashboard_title, type_='dash-db')
  folder_uid = get_folder(folder_title)['uid']
  return next((item for item in dashboards if item['title'] == dashboard_title and item['folderUid'] == folder_uid), None)
  
def addTeamToDashboard(team_name, folder_title, dashboard_title, role):
  if role=='Viewer':
    permission = 1
  elif role=='Editor':
    permission = 2
  
  team_id = grafana_api.teams.get_team_by_name(team_name)[0]['id']
  dashboard_id = get_dashboard(folder_title, dashboard_title)['id']
  items = grafana_api.dashboard.get_dashboard_permissions(dashboard_id)
  #Add team if not present in the folder permission
  if not next((item for item in items if item['teamId'] == team_id), None):
    updated_items = list()
    for item in items:
      if not item.get('inherited',False):
        updated_items.append(item)
        
    updated_items.append({'teamId': team_id, 'permission': permission, "permissionName": role})
    permissions = {'items': updated_items}
    return grafana_api.dashboard.update_dashboard_permissions(dashboard_id, permissions)
  else:
    return {'message': 'Team already present'}

def main():
  valid_ids = []
  HEADERS = {'Authorization': 'Basic '+base64.b64encode(('admin:'+password).encode('ascii')).decode('ascii'), 'Content-type': 'application/json'}
  with open(config_file, 'r') as stream:
    try:
      config = yaml.safe_load(stream)
      users = config.get('users',[])
      teams = dict()
      
      #Iterate trough users creating them
      for user in users:
        print("Creating user "+user['login']+"...")
        user['password']=get_user_password(user['login'],info=user)
        createUser(user)
        #content = update_user_preferences(user['login'],{'theme': 'light'})
      
      #Add all users listed as vierwer to the 'general_viewer' team 
      if ("viewer" in config):
        #Create a team to provide viewer rigths to all dashboards
        #general_viewer
        print("Creating general_viewer team...")
        createTeam('general_viewer')
        teams['general_viewer']=list()
        viewer = config["viewer"]
        for user in viewer:
          print("Adding user "+user+" to \'general_viewer\' team...")
          teams['general_viewer'].append(user)
          addUserToTeam(user,'general_viewer')
      
      #Add all users listed as editor to the 'general_editor' team    
      if ("editor" in config):
        #Create a team to provide editor rights to all dashboards
        #general_editor
        print("Creating general_editor team...")
        createTeam('general_editor')
        teams['general_editor']=list()
        editor = config["editor"]
        for user in editor:
          print("Adding user "+user+" to \'general_editor\' team...")
          teams['general_editor'].append(user)
          addUserToTeam(user,'general_editor')

      #Create general dashboard json
      main_dashboard_json = json.loads(folder_dashboard_template_json)
      main_dashboard_json['dashboard']['title'] = config['name']
      main_dashboard_json['dashboard']['tags'] = [ 'general' ]
      main_dashboard_json['folderId'] = 0
      main_dashboard_next_y = 0
          
      #If general dashboard already exists in grafana reuse id and uid
      general_dashboard_url = 'http://' + GRAFANA_URL + '/api/search?type=dash-db&tag=general&query='+config['name']
      general_dashboard_list = json.loads(requests.get(url=general_dashboard_url, headers=HEADERS).content)
      if len(general_dashboard_list) > 0:
        general_dashboard_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/' + general_dashboard_list[0]['uid']
        tmp = json.loads(requests.get(url=general_dashboard_url, headers=HEADERS).content)
        main_dashboard_json['dashboard']['id'] = tmp['dashboard']['id']
        main_dashboard_json['dashboard']['uid'] = tmp['dashboard']['uid'] 

      cont3 = 0 
      directories = config['directory']
      for directory in directories:
        dir_name = directory['name']
        cont2 = 0
        
        #Separator row for main dashboard
        row = {
          "collapsed": False,
          "datasource": None,
          "gridPos": {
            "h": 1,
            "w": 24,
            "x": 0,
            "y": main_dashboard_next_y
          },
          "id": 300+cont3,
          "panels": [],
          "title": dir_name,
          "type": "row"
        }
        main_dashboard_json['dashboard']['panels'].append(row)
        
        #Create folder only if it does not exist
        folder_url = 'http://' + GRAFANA_URL + '/api/search?type=dash-folder&query='+dir_name
        folder_list = json.loads(requests.get(url=folder_url, headers=HEADERS).content)
        if len(folder_list) > 0:
          folder_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/' + folder_list[0]['uid']
          folder = json.loads(requests.get(url=folder_url, headers=HEADERS).content)['dashboard']
        else:
          folder = createFolder(dir_name)

        folderId = folder['id']
        folder_uid = folder['uid']
        valid_ids.append(folderId)
      
        #Remove default permissions - COMMENTED TO ALLOW GUEST USER TO SEE ALL DASHBOARDS
        #grafana_api.folder.update_folder_permissions(folder_uid, {'items': []})
        #Add 'general' teams permissions
        addTeamToFolder('general_viewer', folder_uid, 'Viewer')
        addTeamToFolder('general_editor', folder_uid, 'Editor')
        
        
        #Initialize folder dashboard json
        folder_dashboard_json = json.loads(folder_dashboard_template_json)
        folder_dashboard_json['dashboard']['title'] = dashboard_config['messages'][language]['overview_dashboard']['title']
        folder_dashboard_json['dashboard']['tags'] = [ 'area' ]
        folder_dashboard_json['folderId'] = folderId
        
        #If general dashboard already exists in grafana reuse id and uid
        folder_dashboard_url = 'http://' + GRAFANA_URL + '/api/search?type=dash-db&tag=area&query='+dashboard_config['messages'][language]['overview_dashboard']['title']
        folder_dashboard_list = json.loads(requests.get(url=folder_dashboard_url, headers=HEADERS).content)
        for dashboard in folder_dashboard_list:
          if dashboard['folderId'] == folderId:
              folder_dashboard_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/' + dashboard['uid']
              tmp = json.loads(requests.get(url=folder_dashboard_url, headers=HEADERS).content)
              folder_dashboard_json['dashboard']['id'] = tmp['dashboard']['id']
              folder_dashboard_json['dashboard']['uid'] = tmp['dashboard']['uid']
        
        #Add all users listed as vierwer to the directory viewer team 
        if ("viewer" in directory):
          #Create a team to provide viewer rights to all dashboards in the directory
          print("  Creating \'"+dir_name+"_viewer\' team...")
          createTeam(dir_name+'_viewer')
          teams[dir_name+'_viewer']=list()
          addTeamToFolder(dir_name+'_viewer', folder_uid, 'Viewer')
          
          viewer = directory["viewer"]
          for user in viewer:
            print("    Adding user \'"+user+"\' to \'"+dir_name+"_viewer\' team...")
            teams[dir_name+'_viewer'].append(user)
            addUserToTeam(user,dir_name+'_viewer')
        
        #Add all users listed as editor to the directory editor team    
        if ("editor" in directory):
          #Create a team to provide editor rights to all dashboards in the directory
          print("  Creating \'"+dir_name+"_editor\' team...")
          createTeam(dir_name+'_editor')
          teams[dir_name+'_editor']=list()
          addTeamToFolder(dir_name+'_editor', folder_uid, 'Editor')
          
          editor = directory["editor"]
          for user in editor:
            print("    Adding user \'"+user+"\' to \'"+dir_name+"_editor\' team...")
            teams[dir_name+'_editor'].append(user)
            addUserToTeam(user,dir_name+'_editor')
            
        #Iterate through all devices
        cont = 0
        for device in directory["device"]:
          dev_name = device["name"]
          dev_uid = device["uid"]
          print('  '+dev_name+':')
          
          #Check if there is alredy a dashboard called <dev_name> in folder <folderId>
          existe = False
          sensor_dashboard_list_url = 'http://' + GRAFANA_URL + '/api/search?type=dash-db&query='+dev_name
          sensor_dashboard_list = json.loads(requests.get(url=sensor_dashboard_list_url, headers=HEADERS).content)
          for dashboard in sensor_dashboard_list:
            if 'folderId' in dashboard and dashboard['folderId'] == folderId:
              existe = True
              sensor_dashboard_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/' + dashboard['uid']
              device_dashboard = json.loads(requests.get(url=sensor_dashboard_url, headers=HEADERS).content)['dashboard']
              break

          if (not existe):
            #Create device detailed dashboard
            print("    Creating device \'"+dev_name+"\' dashboard..." )
            dashboard_json = json.loads(device_dashboard_template_json)
            dashboard_json['dashboard']['title'] = dev_name
            
            dashboard_json['dashboard']['panels'][0]['title'] = dashboard_config['messages'][language]['device_dashboard']['CO2']['title']
            dashboard_json['dashboard']['panels'][0]['description'] = dashboard_config['messages'][language]['device_dashboard']['CO2']['description'][0] + dev_name + \
              dashboard_config['messages'][language]['device_dashboard']['CO2']['description'][1] + dev_uid
            dashboard_json['dashboard']['panels'][0]['targets'][0]['expr'] = "CO2{exported_job=\""+dev_uid+"\"}"
            dashboard_json['dashboard']['panels'][0]['thresholds'][0]['value'] = dashboard_config['overview_dashboards']['thresholds']['warning']
            dashboard_json['dashboard']['panels'][0]['thresholds'][1]['value'] = dashboard_config['overview_dashboards']['thresholds']['caution']
            
            dashboard_json['dashboard']['panels'][1]['title'] = dashboard_config['messages'][language]['device_dashboard']['temperature']['title']
            dashboard_json['dashboard']['panels'][1]['description'] = dashboard_config['messages'][language]['device_dashboard']['temperature']['description'][0] + dev_name + \
              dashboard_config['messages'][language]['device_dashboard']['temperature']['description'][1] + dev_uid
            dashboard_json['dashboard']['panels'][1]['targets'][0]['expr'] = "Temperature{exported_job=\""+dev_uid+"\"}"
            
            dashboard_json['dashboard']['panels'][2]['title'] = dashboard_config['messages'][language]['device_dashboard']['humidity']['title']
            dashboard_json['dashboard']['panels'][2]['description'] = dashboard_config['messages'][language]['device_dashboard']['humidity']['description'][0] + dev_name + \
              dashboard_config['messages'][language]['device_dashboard']['humidity']['description'][1] + dev_uid
            dashboard_json['dashboard']['panels'][2]['targets'][0]['expr'] = "Humidity{exported_job=\""+dev_uid+"\"}"
            dashboard_json['folderId'] = folderId
            dashboard = grafana_api.dashboard.update_dashboard(dashboard_json)
            sensor_dashboard_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/' + dashboard['uid']
            device_dashboard = json.loads(requests.get(url=sensor_dashboard_url, headers=HEADERS).content)['dashboard']
          
          warning = device_dashboard['panels'][0]['thresholds'][0]['value']
          caution = device_dashboard['panels'][0]['thresholds'][1]['value']
          valid_ids.append(device_dashboard['id'])
          
          #Create device CO2 panel
          device_panel_url='http://' + GRAFANA_URL + '/d/' + device_dashboard['uid'] + '/' + device_dashboard['title']
          device_panel_json = json.loads(device_panel_template_json)
          device_panel_json['type'] = panel_type
          device_panel_json['title'] = dev_name
          device_panel_json['links'][0]['title'] = dashboard_config['messages'][language]['overview_dashboard']['link']+dev_name
          device_panel_json['links'][0]['url'] = device_panel_url
          device_panel_json['links'][0]['targetBlank'] = True
          device_panel_json['fieldConfig']['defaults']['links'] = list()
          device_panel_json['fieldConfig']['defaults']['links'].append(dict())
          device_panel_json['fieldConfig']['defaults']['links'][0]['title'] = dashboard_config['messages'][language]['overview_dashboard']['link']+dev_name
          device_panel_json['fieldConfig']['defaults']['links'][0]['url'] = device_panel_url
          device_panel_json['fieldConfig']['defaults']['links'][0]['targetBlank'] = True
          device_panel_json["gridPos"]['x'] = 0
          device_panel_json["gridPos"]['y'] = 0
          device_panel_json["gridPos"]['w'] = w_panel
          device_panel_json["gridPos"]['h'] = h_panel
          device_panel_json['targets'][0]['expr'] = "CO2{exported_job=\""+dev_uid+"\"}"
          device_panel_json['fieldConfig']['defaults']['thresholds']['steps'][2]['value'] = warning
          device_panel_json['fieldConfig']['defaults']['thresholds']['steps'][3]['value'] = caution
          device_panel_json['id'] = cont3+2
          if panel_type == 'stat':
            device_panel_json['options']['colorMode'] = 'background'
            device_panel_json['options']['graphMode'] = 'none'
            device_panel_json['targets'][0]['legendFormat'] = dashboard_config['messages'][language]['device_dashboard']['CO2']['title']
            device_panel_json['targets'].append({'expr': "Temperature{exported_job=\""+dev_uid+"\"}"})
            device_panel_json['targets'][1]['legendFormat'] = dashboard_config['messages'][language]['device_dashboard']['temperature']['title']
            device_panel_json['targets'][1]['refId'] = "B"
            device_panel_json['targets'].append({'expr': "Humidity{exported_job=\""+dev_uid+"\"}"})
            device_panel_json['targets'][2]['legendFormat'] = dashboard_config['messages'][language]['device_dashboard']['humidity']['title']
            device_panel_json['targets'][2]['refId'] = "C"
          
          #Add panel to folder dashboard
          device_panel_json["gridPos"]['x'] = int(cont%num_panel_per_row)*w_panel
          device_panel_json["gridPos"]['y'] = int(cont/num_panel_per_row)*h_panel
          folder_dashboard_json['dashboard']['panels'].append(dict(device_panel_json))
          
          #add panel to main dashboard
          x = int(cont2%num_panel_per_row)*w_panel
          y = int(cont2/num_panel_per_row)*h_panel + 1 + main_dashboard_next_y
          #y_local = int(cont2/num_panel_per_row)*h_panel
          #if not y_local: y+=main_dashboard_y_offset
          device_panel_json["gridPos"]['x'] = x
          device_panel_json["gridPos"]['y'] = y
          main_dashboard_json['dashboard']['panels'].append(dict(device_panel_json))
          #print(main_dashboard_json['dashboard']['panels'][-1]['title'])
          #print(yaml.safe_dump(main_dashboard_json['dashboard']['panels'][-1]['fieldConfig']['defaults']['thresholds']['steps']))
          
          cont+=1
          cont2+=1
          cont3+=1
          
          #Add all users listed as vierwer to the device viewer team
          if ("viewer" in device):
            #Create team to provide viewer rights to the device dashboard
            print("    Creating \'"+dir_name+"_"+dev_name+"_viewer\' team...")
            createTeam(dir_name+"_"+dev_name+'_viewer')
            teams[dir_name+"_"+dev_name+'_viewer']=list()
            addTeamToDashboard(dir_name+"_"+dev_name+'_viewer', folder['title'], dev_name, 'Viewer')
            addTeamToDashboard(dir_name+"_"+dev_name+'_viewer', folder['title'], dev_name+' CO2', 'Viewer')
            
            viewer = device["viewer"]
            for user in viewer:
              print("      Adding user \'"+user+"\' to \'"+dir_name+"_"+dev_name+"_viewer\' team...")
              teams[dir_name+"_"+dev_name+'_viewer'].append(user)
              addUserToTeam(user,dir_name+"_"+dev_name+'_viewer')
              update_user_preferences(user,{'homeDashboardId': device_CO2_dashboard['id']})
              
          #Add all users listed as editor to the device viewer team
          if ("editor" in device):
            #Create team to provide editor rights to the device dashboard
            print("    Creating \'"+dir_name+"_"+dev_name+"_editor\' team...")
            createTeam(dir_name+"_"+dev_name+'_editor')
            teams[dir_name+"_"+dev_name+'_editor']=list()
            addTeamToDashboard(dir_name+"_"+dev_name+'_editor', folder['title'], dev_name, 'Editor')
            
            editor = device["editor"]
            for user in editor:
              print("      Adding user \'"+user+"\' to \'"+dir_name+"_"+dev_name+"_editor\' team...")
              teams[dir_name+"_"+dev_name+'_editor'].append(user)
              addUserToTeam(user,dir_name+"_"+dev_name+'_editor')
              
        main_dashboard_next_y = y + h_panel
          
        #Create summary dashboard for directory 
        print("  Creating \'"+dir_name+"\' dashboard..." )
        dashboard=grafana_api.dashboard.update_dashboard(folder_dashboard_json)
        valid_ids.append(dashboard['id'])
      
      #Create general summay dashboard
      print("Creating \'"+config['name']+"\' dashboard..." )
      main_dashboard=grafana_api.dashboard.update_dashboard(main_dashboard_json)
      valid_ids.append(main_dashboard['id'])
      ##print(yaml.safe_dump(main_dashboard_json['dashboard']['panels']))
     
      users_passwords['admin'] = password
      update_user_preferences('admin', {'homeDashboardId': main_dashboard['id']})
      update_org_preferences({'homeDashboardId': main_dashboard['id']})
      
      #Delete all folders and dashboards that were not present it the config file
      items_list_url = 'http://' + GRAFANA_URL + '/api/search'
      items_list = json.loads(requests.get(url=items_list_url, headers=HEADERS).content)
      for item in items_list:
        if not item['id'] in valid_ids:
          print('Deleting uid='+item['uid'])
          items_list_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/'+item['uid']
          requests.delete(url=items_list_url, headers=HEADERS)

    except yaml.YAMLError as exc:
      print(exc)

if __name__ == "__main__":
  main()

