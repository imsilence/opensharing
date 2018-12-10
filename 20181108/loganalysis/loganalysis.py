#encoding: utf-8
import logging
import traceback
import os
import time
from datetime import datetime
from argparse import ArgumentParser
import shutil

from jinja2 import FileSystemLoader, Environment
from geoip2.database import Reader

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def stat_days(infile):
    '''统计每天日志数据
    '''
    day_data = {}
    with open(infile, 'r', encoding="utf-8") as fhandler:
        for line in fhandler:
            try:
                #解析每行日志内容
                _nodes = line.split()
                #跳过可能错误的字段
                if len(_nodes) < 12:
                    continue
                #         ip         datetime       method         url       status    bytes
                #print(_nodes[0], _nodes[3][1:], _nodes[5][1:], _nodes[6], _nodes[8], _nodes[9])
                _day = datetime.strptime(_nodes[3][1:], '%d/%b/%Y:%H:%M:%S').strftime('%Y-%m-%d')
                # 设置每天的默认值
                day_data.setdefault(_day, {'hits' : 0, 'vistors' : {}, 'status' : {}, 'bytes' : 0})
                # 设置每出现的IP的访问次数默认为0
                day_data[_day]['vistors'].setdefault(_nodes[0], 0)
                # 设置每天出现的状态码默认值为0
                day_data[_day]['status'].setdefault(_nodes[8], 0)

                #统计数据
                day_data[_day]['hits'] += 1
                day_data[_day]['vistors'][_nodes[0]] += 1
                day_data[_day]['status'][_nodes[8]] += 1
                day_data[_day]['bytes'] += int(_nodes[9]) if _nodes[9].isdigit() else 0
            except Exception as e:
                logger.error(e)
                logger.error(traceback.format_exc())
    return sorted(day_data.items(), key=lambda x: x[0]) #将key:value转为为(key, value)的list并根据key进行排序


def stat_total(days):
    '''统计总数据
    '''
    total_data = {'hits' : 0, 'vistors' : {}, 'status' : {}, 'bytes' : 0}

    for _day, _stat in days:
        total_data['hits'] += _stat['hits']    #访问量为每天访问量和
        total_data['bytes'] += _stat['bytes']  #流量为每天流量和

        for _ip, _cnt in _stat['vistors'].items(): #访问用户为每天访问IP列表合并
            total_data['vistors'].setdefault(_ip, 0)
            total_data['vistors'][_ip] += _cnt

        for _status, _cnt in _stat['status'].items(): #访问状态码为每天隔访问状态码和
            total_data['status'].setdefault(_status, 0)
            total_data['status'][_status] += _cnt

    return total_data


def stat_region(total_data):
    '''统计区域数据
    '''
    region_data = {}
    region_location = {}

    #打开maxmind mmdb文件
    geoip2_reader = Reader(os.path.join(BASE_DIR, 'db', 'GeoLite2-City.mmdb'))

    for _ip, _cnt in total_data['vistors'].items():
        try:
            _city = geoip2_reader.city(_ip) #获取ip对应城市信息

            #只显示国内IP地址
            if _city.country.names.get('zh-CN', '') != '中国':
                continue

            #获取国家和城市信息
            _city_name = '{}/{}'.format(_city.country.names.get('zh-CN', ''), _city.city.names.get('zh-CN', ''))

            region_data.setdefault(_city_name, 0)

            #统计每天城市发生访问次数
            region_data[_city_name] += _cnt

            #记录城市对应经纬度
            region_location[_city_name] = [_city.location.longitude, _city.location.latitude]
        except BaseException as e:
            logger.error(e)

    #关闭文件
    geoip2_reader.close()
    return region_data, region_location


def main(infile, outdir):
    '''主程序
    '''

    #获取各种统计结果
    day_data = stat_days(infile) #每天统计项
    total_data = stat_total(day_data) #总统计项
    region_data, region_location = stat_region(total_data) #区域统计项

    #创建文件加载器
    env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, 'tpl')))

    #获取模板
    template = env.get_template('index.html')
    with open(os.path.join(outdir, 'index.html'), 'w', encoding="utf-8") as fhandler:
        #渲染模板并写入文件
        fhandler.write(template.render(day_data=day_data,
                                        total_data=total_data,
                                        region_data=region_data,
                                        region_location=region_location))


if __name__ == "__main__":
    #配置日志记录
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s:%(message)s")

    #定义命令行解析器
    parser = ArgumentParser()

    parser.add_argument("-i", "--infile", type=str, default="access.log", help="log file")
    parser.add_argument("-o", "--outdir", type=str, help="report dir")

    #解析命令行参数
    args = parser.parse_args()

    #将文件路径转化为绝对路径
    infile = os.path.abspath(args.infile)
    outdir = os.path.abspath(args.outdir or 'reports/report_{0}'.format(int(time.time() * 1000)))

    #验证解析文件和输出目录是否存在
    if not os.path.exists(infile):
        logger.error("input file not exists: %s", infile)
    elif os.path.exists(outdir):
        logger.error("output dir is exists: %s", outdir)
    else:
        #复制模板文件
        shutil.copytree(os.path.join(BASE_DIR, 'tpl'), outdir)

        #运行主程序
        main(infile, outdir)

        #记录日志
        logger.info("generate report to: %s", outdir)