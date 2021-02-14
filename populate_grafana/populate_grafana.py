#!/usr/bin/env python

import re
import unidecode
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
valid_ids = []
file = open('config.yaml')
dashboard_config = yaml.safe_load(file.read())
file.close()
GRAFANA_URL=sys.argv[1]
GRAFANA_IP=GRAFANA_URL.split(':')[0]
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
file = open('editor_dashboard.json')
editor_dashboard_template_json = file.read()
file.close()

def createUpdateDashboard(jsonFile, tag):
  tag_url = 'http://' + GRAFANA_URL + '/api/search?tag=' + tag
  HEADERS = {'Authorization': 'Basic '+base64.b64encode(('admin:'+password).encode('ascii')).decode('ascii'), 'Content-type': 'application/json'}
  tag_list = json.loads(requests.get(url=tag_url, headers=HEADERS).content)
  if len(tag_list) == 0:
    print('Create dashboard from '+jsonFile)
    file = open(jsonFile)
    db_json = file.read()
    file.close()
    db = json.loads(db_json)
    db['tags'] = [tag]
    id = grafana_api.dashboard.update_dashboard({'dashboard': db})['id']
  else:
    id = tag_list[0]['id']
  valid_ids.append(id)

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
    data = json.dumps({
        "uid": re.sub('[^A-Za-z0-9]+', '', unidecode.unidecode(title)).lower()+'folder',
        "title": title
    })
    url = 'http://' + GRAFANA_URL + '/api/folders'
    headers = {'Authorization': 'Basic '+base64.b64encode(('admin:'+password).encode('ascii')).decode('ascii'), 'Content-type': 'application/json'}
    folder = post(url, data,  headers)
  return json.loads(folder)

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
  HEADERS = {'Authorization': 'Basic '+base64.b64encode(('admin:'+password).encode('ascii')).decode('ascii'), 'Content-type': 'application/json'}
  with open(config_file, 'r') as stream:
    try:
      config = yaml.safe_load(stream)
      users = config.get('users',[])
      teams = dict()

      createTeam('devicemanager')

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

      #Create generic dashboards QR and detalle
      createUpdateDashboard('detalle.json', 'detail')

       #Create (if it does not extist) QR dashboard
      qr_url = 'http://' + GRAFANA_URL + '/api/search?tag=QR'
      qr_list = json.loads(requests.get(url=qr_url, headers=HEADERS).content)
      if len(qr_list) == 0:
        print('Create QR dashboard')
        file = open('QR.json')
        qr_dashboard_template_json = file.read()
        file.close()
        qr_dashboard_json = json.loads(qr_dashboard_template_json)
        qr_dashboard_json['tags'] = ['QR']
        qr_dashboard_json['uid'] = 'lastvalue'
        qr_dashboard_json['links'][0]['url'] = 'http://' + GRAFANA_IP +'/d/detail?var-uid=$uid&var-name=$name'
        qr_dashboard_json['links'][1]['url'] = 'http://' + GRAFANA_URL + \
        '/d/editor/editor?var-id=$uid&var-Warning=700&var-Caution=1000' + \
        '&var-db_uid=$uid&var-name=$name&var-Alarm=ON' + \
        '&var-FRC=OFF&var-update=OFF&var-factory_reset=OFF' + \
        '&var-ABC=OFF&var-reboot=OFF' + \
        '&var-MQTT_server=' + GRAFANA_IP

        qr_dashboard = grafana_api.dashboard.update_dashboard({'dashboard': qr_dashboard_json})
        valid_ids.append(qr_dashboard['id'])
      else:
        valid_ids.append(qr_list[0]['id'])

      #Create "hiden" folder only if it does not exist
      folder_url = 'http://' + GRAFANA_URL + '/api/search?type=dash-folder&query=hiden'
      folder_list = json.loads(requests.get(url=folder_url, headers=HEADERS).content)
      if len(folder_list) > 0:
        folder_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/' + folder_list[0]['uid']
        folder = json.loads(requests.get(url=folder_url, headers=HEADERS).content)['dashboard']
      else:
        folder = createFolder('hiden')
        grafana_api.folder.update_folder_permissions(folder['uid'], {'items': []})
        addTeamToFolder('devicemanager', folder['uid'], 'Viewer')

      folderId = folder['id']
      folder_uid = folder['uid']
      valid_ids.append(folderId)

      #Create (if it does not extist) dashboard to manage thredsholds
      editor_url = 'http://' + GRAFANA_URL + '/api/search?tag=editor'
      editor_list = json.loads(requests.get(url=editor_url, headers=HEADERS).content)
      if len(editor_list) == 0:
        print('Create dashboard editor')
        editor_dashboard_json = json.loads(editor_dashboard_template_json)
        editor_dashboard_json['uid'] = 'editor'
        editor_dashboard_json['panels'][0]['options']['url'] = 'http://' + GRAFANA_URL.split(':')[0]+':30880/update'
        editor_dashboard = grafana_api.dashboard.update_dashboard({'folderId': folderId, 'dashboard': editor_dashboard_json})
        valid_ids.append(editor_dashboard['id'])
      else:
        valid_ids.append(editor_list[0]['id'])

      #Create general dashboard json
      main_dashboard_json = json.loads(folder_dashboard_template_json)
      main_dashboard_json['dashboard']['title'] = config['name']
      main_dashboard_json['dashboard']['tags'] = [ 'general' ]
      main_dashboard_json['folderId'] = 0
      main_dashboard_json['dashboard']['uid'] = 'general'
      main_dashboard_next_y = 0

      #If general dashboard already exists in grafana reuse id and uid
      general_dashboard_url = 'http://' + GRAFANA_URL + '/api/search?type=dash-db&tag=general&query='+config['name']
      general_dashboard_list = json.loads(requests.get(url=general_dashboard_url, headers=HEADERS).content)
      if len(general_dashboard_list) > 0:
        general_dashboard_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/' + general_dashboard_list[0]['uid']
        tmp = json.loads(requests.get(url=general_dashboard_url, headers=HEADERS).content)
        main_dashboard_json['dashboard']['id'] = tmp['dashboard']['id']

      cont3 = 0
      directories = config['directory']
      for directory in directories:
        dir_name = directory['name']
        cont2 = 0

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

        #Remove default permissions if there are 'viewer' or 'editor' users
        restrict_access = False
        if 'viewer' in directory or 'editor' in directory:
            restrict_access = True
            grafana_api.folder.update_folder_permissions(folder_uid, {'items': []})

        #Separator row for main dashboard
        if not restrict_access:
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

        #Add 'general' teams permissions
        if 'viewer' in config:
          addTeamToFolder('general_viewer', folder_uid, 'Viewer')
        if 'editor' in config:
          addTeamToFolder('general_editor', folder_uid, 'Editor')

        #Initialize folder dashboard json
        folder_dashboard_json = json.loads(folder_dashboard_template_json)
        folder_dashboard_json['dashboard']['title'] = dashboard_config['messages'][language]['overview_dashboard']['title']
        folder_dashboard_json['dashboard']['tags'] = [ 'area' ]
        folder_dashboard_json['dashboard']['uid'] = re.sub('[^A-Za-z0-9]+', '', unidecode.unidecode(folder['title'])).lower()
        folder_dashboard_json['folderId'] = folderId

        #If folder dashboard already exists in grafana reuse id
        folder_dashboard_url = 'http://' + GRAFANA_URL + '/api/search?type=dash-db&tag=area&query='+dashboard_config['messages'][language]['overview_dashboard']['title']
        folder_dashboard_list = json.loads(requests.get(url=folder_dashboard_url, headers=HEADERS).content)
        for dashboard in folder_dashboard_list:
          if dashboard['folderId'] == folderId:
              folder_dashboard_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/' + dashboard['uid']
              tmp = json.loads(requests.get(url=folder_dashboard_url, headers=HEADERS).content)
              folder_dashboard_json['dashboard']['id'] = tmp['dashboard']['id']

        #Create area detailed dashboard
        print("  Creating area detailed dashboard..." )
        detail_json = json.loads(device_dashboard_template_json)
        detail_json['dashboard']['title'] = dashboard_config['messages'][language]['detail_dashboard']['title']
        detail_json['dashboard']['uid'] = re.sub('[^A-Za-z0-9]+', '', unidecode.unidecode(folder['title'])).lower()+'det'
        detail_json['folderId'] = folderId

        detail_json['dashboard']['panels'][0]['title'] = dashboard_config['messages'][language]['device_dashboard']['CO2']['title']
        detail_json['dashboard']['panels'][1]['title'] = dashboard_config['messages'][language]['device_dashboard']['temperature']['title']
        detail_json['dashboard']['panels'][2]['title'] = dashboard_config['messages'][language]['device_dashboard']['humidity']['title']

        detail_json['dashboard']['panels'][0]['fill'] = 0
        detail_json['dashboard']['panels'][1]['fill'] = 0
        detail_json['dashboard']['panels'][2]['fill'] = 0

        detail_json['dashboard']['panels'][0]['targets'] = []
        detail_json['dashboard']['panels'][1]['targets'] = []
        detail_json['dashboard']['panels'][2]['targets'] = []

        #Iterate through all devices
        cont = 0
        for device in directory["device"]:
          dev_name = str(device["name"])
          dev_uid = device["uid"]
          #if there is an overwrite field that equals to True then the device
          #dashboard must be overwriten
          overwrite = device.get('overwrite', False)
          print('  '+str(dev_name)+':')

          #If not overgwrite check if there is alredy a dashboard with this id
          existe = False
          if not overwrite:
            url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/'+str(dev_uid)
            response = requests.get(url=url, headers=HEADERS)
            if response.status_code == 200:
                existe = True
                content = json.loads(response.content)
                device_dashboard = content['dashboard']
                dev_name = device_dashboard['title']
                #if it is in a different folder update dashboard with folderId
                if content['meta']['folderId'] != folderId:
                    dashboard_json = {'folderId': folderId, 'dashboard': device_dashboard}
                    dashboard = grafana_api.dashboard.update_dashboard(dashboard_json)


          #Add device to the area device dashboards
          detail_json['dashboard']['panels'][0]['targets'].append({'expr': "CO2{exported_job=\""+str(dev_uid)+"\"}", 'legendFormat': dev_name, 'refId': dev_name})
          detail_json['dashboard']['panels'][1]['targets'].append({'expr': "Temperature{exported_job=\""+str(dev_uid)+"\"}", 'legendFormat': dev_name, 'refId': dev_name})
          detail_json['dashboard']['panels'][2]['targets'].append({'expr': "Humidity{exported_job=\""+str(dev_uid)+"\"}", 'legendFormat': dev_name, 'refId': dev_name})

          if (not existe):
            #Create device detailed dashboard
            print("    Creating device \'"+str(dev_name)+"\' dashboard..." )
            dashboard_json = json.loads(device_dashboard_template_json)
            dashboard_json['dashboard']['title'] = str(dev_name)
            dashboard_json['dashboard']['uid'] = str(dev_uid)

            editor_url = 'http://' + GRAFANA_URL + '/api/search?tag=editor'
            editor_uid = json.loads(requests.get(url=editor_url, headers=HEADERS).content)[0]['uid']

            dashboard_json['dashboard']['links'] = [{
              'icon': 'dashboard',
              'targetBlank': True,
              'title': 'Editor',
              'type': 'link',
              'url': 'http://' + GRAFANA_URL + '/d/' + editor_uid + '/editor?var-id=' + str(dev_uid) + \
                      '&var-name=' + str(dev_name) + \
                      '&var-Warning=' + str(dashboard_config['overview_dashboards']['thresholds']['warning']) + \
                      '&var-Caution=' + str(dashboard_config['overview_dashboards']['thresholds']['caution'])  + \
                      '&var-db_uid=' + str(dev_uid) + '&var-folderId=' + str(folderId) + \
                      '&var-Alarm=ON&var-FRC=OFF&var-update=OFF' + \
                      '&var-ABC=OFF&var-reboot=OFF' + \
                      '&var-factory_reset=OFF&var-MQTT_server=' + GRAFANA_IP
            }]
            dashboard_json['dashboard']['panels'][0]['title'] = dashboard_config['messages'][language]['device_dashboard']['CO2']['title']
            dashboard_json['dashboard']['panels'][0]['description'] = dashboard_config['messages'][language]['device_dashboard']['CO2']['description'][0] + str(dev_name) + \
              dashboard_config['messages'][language]['device_dashboard']['CO2']['description'][1] + str(dev_uid)
            dashboard_json['dashboard']['panels'][0]['targets'][0]['expr'] = "CO2{exported_job=\""+str(dev_uid)+"\"}"
            dashboard_json['dashboard']['panels'][0]['thresholds'][0]['value'] = dashboard_config['overview_dashboards']['thresholds']['warning']
            dashboard_json['dashboard']['panels'][0]['thresholds'][1]['value'] = dashboard_config['overview_dashboards']['thresholds']['caution']

            dashboard_json['dashboard']['panels'][1]['title'] = dashboard_config['messages'][language]['device_dashboard']['temperature']['title']
            dashboard_json['dashboard']['panels'][1]['description'] = dashboard_config['messages'][language]['device_dashboard']['temperature']['description'][0] + str(dev_name) + \
              dashboard_config['messages'][language]['device_dashboard']['temperature']['description'][1] + str(dev_uid)
            dashboard_json['dashboard']['panels'][1]['targets'][0]['expr'] = "Temperature{exported_job=\""+str(dev_uid)+"\"}"

            dashboard_json['dashboard']['panels'][2]['title'] = dashboard_config['messages'][language]['device_dashboard']['humidity']['title']
            dashboard_json['dashboard']['panels'][2]['description'] = dashboard_config['messages'][language]['device_dashboard']['humidity']['description'][0] + str(dev_name) + \
              dashboard_config['messages'][language]['device_dashboard']['humidity']['description'][1] + str(dev_uid)
            dashboard_json['dashboard']['panels'][2]['targets'][0]['expr'] = "Humidity{exported_job=\""+str(dev_uid)+"\"}"
            dashboard_json['folderId'] = folderId
            dashboard = grafana_api.dashboard.update_dashboard(dashboard_json)
            sensor_dashboard_url = 'http://' + GRAFANA_URL + '/api/dashboards/uid/' + dashboard['uid']
            device_dashboard = json.loads(requests.get(url=sensor_dashboard_url, headers=HEADERS).content)['dashboard']

          warning = device_dashboard['panels'][0]['thresholds'][0]['value']
          #If alarm is declared in the device only one threshold appears, that is the one defined ty the alarm.
          if len(device_dashboard['panels'][0]['thresholds']) > 1:
            caution = device_dashboard['panels'][0]['thresholds'][1]['value']
          else:
            caution = dashboard_config['overview_dashboards']['thresholds']['caution']
          valid_ids.append(device_dashboard['id'])

          #Create device CO2 panel
          device_panel_url='http://' + GRAFANA_IP + '/d/' + device_dashboard['uid']
          device_panel_json = json.loads(device_panel_template_json)
          device_panel_json['type'] = panel_type
          device_panel_json['title'] = str(dev_name)
          device_panel_json['links'][0]['title'] = dashboard_config['messages'][language]['overview_dashboard']['link']+str(dev_name)
          device_panel_json['links'][0]['url'] = device_panel_url
          device_panel_json['links'][0]['targetBlank'] = True
          device_panel_json['fieldConfig']['defaults']['links'] = list()
          device_panel_json['fieldConfig']['defaults']['links'].append(dict())
          device_panel_json['fieldConfig']['defaults']['links'][0]['title'] = dashboard_config['messages'][language]['overview_dashboard']['link']+str(dev_name)
          device_panel_json['fieldConfig']['defaults']['links'][0]['url'] = device_panel_url
          device_panel_json['fieldConfig']['defaults']['links'][0]['targetBlank'] = True
          device_panel_json["gridPos"]['x'] = 0
          device_panel_json["gridPos"]['y'] = 0
          device_panel_json["gridPos"]['w'] = w_panel
          device_panel_json["gridPos"]['h'] = h_panel
          device_panel_json['targets'][0]['expr'] = "CO2{exported_job=\""+str(dev_uid)+"\"}"
          device_panel_json['fieldConfig']['defaults']['thresholds']['steps'][2]['value'] = warning
          device_panel_json['fieldConfig']['defaults']['thresholds']['steps'][3]['value'] = caution
          device_panel_json['id'] = cont3+2
          if panel_type == 'stat':
            device_panel_json['options']['colorMode'] = 'background'
            device_panel_json['options']['graphMode'] = 'none'
            device_panel_json['targets'][0]['legendFormat'] = dashboard_config['messages'][language]['device_dashboard']['CO2']['title']
            device_panel_json['targets'].append({'expr': "Temperature{exported_job=\""+str(dev_uid)+"\"}"})
            device_panel_json['targets'][1]['legendFormat'] = dashboard_config['messages'][language]['device_dashboard']['temperature']['title']
            device_panel_json['targets'][1]['refId'] = "B"
            device_panel_json['targets'].append({'expr': "Humidity{exported_job=\""+str(dev_uid)+"\"}"})
            device_panel_json['targets'][2]['legendFormat'] = dashboard_config['messages'][language]['device_dashboard']['humidity']['title']
            device_panel_json['targets'][2]['refId'] = "C"

          #Add panel to folder dashboard
          device_panel_json["gridPos"]['x'] = int(cont%num_panel_per_row)*w_panel
          device_panel_json["gridPos"]['y'] = int(cont/num_panel_per_row)*h_panel
          folder_dashboard_json['dashboard']['panels'].append(dict(device_panel_json))

          #add panel to main dashboard
          if not restrict_access:
              x = int(cont2%num_panel_per_row)*w_panel
              y = int(cont2/num_panel_per_row)*h_panel + 1 + main_dashboard_next_y
              #y_local = int(cont2/num_panel_per_row)*h_panel
              #if not y_local: y+=main_dashboard_y_offset
              device_panel_json["gridPos"]['x'] = x
              device_panel_json["gridPos"]['y'] = y
              main_dashboard_json['dashboard']['panels'].append(dict(device_panel_json))
              #print(main_dashboard_json['dashboard']['panels'][-1]['title'])
              #print(yaml.safe_dump(main_dashboard_json['dashboard']['panels'][-1]['fieldConfig']['defaults']['thresholds']['steps']))
              cont2+=1

          cont+=1
          cont3+=1

          #Add all users listed as vierwer to the device viewer team
          if ("viewer" in device):
            #Create team to provide viewer rights to the device dashboard
            print("    Creating \'"+dir_name+"_"+str(dev_name)+"_viewer\' team...")
            createTeam(dir_name+"_"+str(dev_name)+'_viewer')
            teams[dir_name+"_"+str(dev_name)+'_viewer']=list()
            addTeamToDashboard(dir_name+"_"+str(dev_name)+'_viewer', folder['title'], str(dev_name), 'Viewer')
            addTeamToDashboard(dir_name+"_"+str(dev_name)+'_viewer', folder['title'], str(dev_name)+' CO2', 'Viewer')

            viewer = device["viewer"]
            for user in viewer:
              print("      Adding user \'"+user+"\' to \'"+dir_name+"_"+str(dev_name)+"_viewer\' team...")
              teams[dir_name+"_"+str(dev_name)+'_viewer'].append(user)
              addUserToTeam(user,dir_name+"_"+str(dev_name)+'_viewer')
              update_user_preferences(user,{'homeDashboardId': device_CO2_dashboard['id']})

          #Add all users listed as editor to the device viewer team
          if ("editor" in device):
            #Create team to provide editor rights to the device dashboard
            print("    Creating \'"+dir_name+"_"+str(dev_name)+"_editor\' team...")
            createTeam(dir_name+"_"+str(dev_name)+'_editor')
            teams[dir_name+"_"+str(dev_name)+'_editor']=list()
            addTeamToDashboard(dir_name+"_"+str(dev_name)+'_editor', folder['title'], str(dev_name), 'Editor')

            editor = device["editor"]
            for user in editor:
              print("      Adding user \'"+user+"\' to \'"+dir_name+"_"+str(dev_name)+"_editor\' team...")
              teams[dir_name+"_"+str(dev_name)+'_editor'].append(user)
              addUserToTeam(user,dir_name+"_"+str(dev_name)+'_editor')

        main_dashboard_next_y = y + h_panel

        #Create summary dashboard for directory
        print("  Creating \'"+dir_name+"\' dashboard..." )
        dashboard=grafana_api.dashboard.update_dashboard(folder_dashboard_json)
        valid_ids.append(dashboard['id'])

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
            update_user_preferences(user,{'homeDashboardId': dashboard['id']})

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
            addUserToTeam(user,'devicemanager')
            update_user_preferences(user,{'homeDashboardId': dashboard['id']})

        #Create detail dashboard for directory
        print("  Creating \'"+dir_name+"\' detail dashboard..." )
        detail_dashboard = grafana_api.dashboard.update_dashboard(detail_json)
        valid_ids.append(detail_dashboard['id'])

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
