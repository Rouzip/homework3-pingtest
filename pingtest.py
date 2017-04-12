import json
import subprocess
import re
from multiprocessing import Pool
from echarts import Echart, Bar
from echarts.option import *
import os


# hostnames(list[str]),nums_packets(int)
# 返回ping网站的原始Json和统计Json
def run_ping_func(hostnames, num_packets):
    # 利用系统自带的ping命令获取目标的时间戳
    originInformation = subprocess.getoutput('ping -c' + \
                    str(num_packets) + ' ' + hostnames).split('\n')


    # 收集原始数据
    reText = re.compile(r'time=(.*)(\sms)')
    # rtt时间表
    rttList = []
    for line in originInformation:
        # 在原始数据中搜索时间戳
        reLine = re.search(reText,line)
        if reLine:
            rttList.append(float(reLine.group(1)))
    # 正则表达式匹配已知的max，avg，min
    reText2 = re.compile(r'(\d+\.\d+)\/(\d+\.\d+)\/(\d+\.\d+)')
    reSear = re.search(reText2,originInformation[-1])
    if not reSear:
        rttMax, rttAvg = -1, -1
    else:
        rttMax, rttAvg = float(reSear.group(3)),float(reSear.group(2))
    rttListLength = len(rttList)
    # 假如有丢弃的数据包，使用-1来填充数据
    if rttListLength < num_packets:
        for i in range(num_packets - rttListLength):
            rttList.append(-1)
    # 使用正则表达式，匹配倒数第二行的丢包率
    dropRate = re.search(re.compile(r'.* (.*%)'), originInformation[-2]).group(1)


    # 生成汇总的统计信息
    statistics = {
                      'drop_rate' : dropRate,
                       'max_rtt' : rttMax,
                       'median_rtt' : rttAvg
                 }
    # 汇总站点，ping原始数据，ping统计数据
    return hostnames, rttList, statistics


# hostnames(list[str]),nums_packets(int),raw_ping_output_filename(str),aggregated_ping_output_filename(str)
# 多进程跑run_ping_func函数
def run_ping(hostnames, num_packets, raw_ping_output_filename, aggregated_ping_output_filename):
    # 记录原始数据与统计数据的汇总
    originInfo = {}
    statisticsInfo = {}
    hostNum = len(hostnames)


    # 建立进程池，并行计算
    try:
        hostPool = Pool(hostNum)
        funcParameter = []
        for i in range(hostNum):
            funcParameter.append((hostnames[i], num_packets))
        internetInfo = hostPool.starmap(run_ping_func, funcParameter)
    except Exception as e:
        print('Something wrong: ' + e.__context__)


    # 将函数返回的信息进行汇总
    for i in internetInfo:
        a, b, c = i
        originInfo[a] = b
        statisticsInfo[a] = c


    # 生成json格式文件并写入文件
    originJson = json.dumps(originInfo)
    statisticsJson = json.dumps(statisticsInfo)
    with open(raw_ping_output_filename, 'a+') as fp:
        fp.write(originJson)
    with open(aggregated_ping_output_filename, 'a+') as fp:
        fp.write(statisticsJson)
    hostPool.close()
    hostPool.join()


# 可视化方案目前定为使用横向柱状图
# 使用echarts模板引擎渲染数据
def viewableData(dataJson):
    statisticInfo = json.loads(dataJson)
    # 拆分Json文件，拆成多个列表
    # 网站列表，最大rtt时间，平均rtt时间，丢包率
    hostList, maxList, avgList, dropRateList  = [], [], [], []
    for i in statisticInfo:
        hostList.append(i)
        maxList.append(statisticInfo[i]['max_rtt'])
        avgList.append(statisticInfo[i]['median_rtt'])
        dropRateList.append(float(statisticInfo[i]['drop_rate'][:-1]))

    # 对网页进行初始化处理
    chart = Echart(title = 'ping结果统计',width = 'auto', height = 'auto')


    # 设置三条数据
    chart.use(Bar('maxList', maxList,tpye =  'vertical'))
    chart.use(Bar('avgList',avgList, tpye = 'vertical'))
    chart.use(Bar('dropRateList',dropRateList, tpye = 'certical'))

    # 设置y轴
    chart.use(Axis('category', 'left', data = hostList, axisLabel = {'interval':0}))


    # 启用显示
    chart.use(Tooltip(trigger = 'axis'))
    # 启用图标
    chart.use(Legend(['maxList','avgList', 'dropRateList'], position = ('center', 'top')))
    # 启用工具栏
    feature = {'dataZoom':{
                   'show': True,
                   'title':{
                       'dataZoom': '区域缩放',
                       'dataZoomReset': '区域缩放后退'
                   }
               },
               'magicType':{
                   'show':True,
                   'type':['line',
                           'bar',
                           'stack',
                           'tiled'
                   ]
               },
               'restore':{
                   'show':True,
                   'title': '还原'
               }
    }
    # 开启工具盒子
    chart.use(Toolbox(feature = feature, orient = 'vertical', show = True))


    # 展示可视化数据
    chart.plot()


    # 存储html
    chart.save(os.getcwd() + '/', 'ping可视化数据')



# 测试为所选网站，并进行ping100次
if __name__ == '__main__':
    fileList = []
    with open('alexa_top_100', 'r') as fp:
        for file in fp.readlines():
            fileList.append(file.strip())
    run_ping(fileList, 100, 'ori.json', 'sta.json')
        
    with open('sta.json','r') as fp:
        testJson = fp.read()
        viewableData(testJson)


    
