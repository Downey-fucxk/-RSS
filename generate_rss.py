from feedgen.feed import FeedGenerator
import requests
from bs4 import BeautifulSoup
import datetime
import re

def fetch_bidding_info():
    """抓取武汉公共资源交易平台的招标信息"""
    base_url = "https://www.whzbtbxt.cn"
    
    # 定义需要抓取的招标信息类型和对应的API路径
    bidding_types = {
        '招标公告': '/whebd-server/tendererNotice/list',
        '变更公告': '/whebd-server/amendBulletin/list', 
        '中标结果': '/whebd-server/winBidBulletin/list',
        '资格预审': '/whebd-server/prequalification/list'
    }
    
    all_items = []
    
    for bid_type, api_path in bidding_types.items():
        try:
            print(f"正在抓取 {bid_type}...")
            
            # 构造API请求URL和参数
            api_url = base_url + api_path
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            }
            
            # 请求参数 - 获取最近30天的数据
            params = {
                'page': 1,
                'limit': 20,
                'startDate': (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
                'endDate': datetime.datetime.now().strftime('%Y-%m-%d')
            }
            
            response = requests.post(api_url, headers=headers, data=params, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and 'data' in data:
                    for item in data['data']:
                        try:
                            # 提取项目信息
                            title = item.get('projectName', '无标题')
                            bulletin_id = item.get('id', '')
                            publish_date = item.get('publishDate', '')
                            
                            # 构造详情页链接
                            if bid_type == '招标公告':
                                detail_url = f"{base_url}/#/cmsIndex?path=tendererNotice&type=detail&id={bulletin_id}"
                            elif bid_type == '变更公告':
                                detail_url = f"{base_url}/#/cmsIndex?path=amendBulletin&type=detail&id={bulletin_id}"
                            elif bid_type == '中标结果':
                                detail_url = f"{base_url}/#/cmsIndex?path=winBidBulletin&type=detail&id={bulletin_id}"
                            else:
                                detail_url = f"{base_url}/#/cmsIndex?path=prequalification&type=detail&id={bulletin_id}"
                            
                            # 处理发布时间
                            pub_date = datetime.datetime.now()
                            if publish_date:
                                try:
                                    pub_date = datetime.datetime.strptime(publish_date, '%Y-%m-%d %H:%M:%S')
                                except:
                                    pub_date = datetime.datetime.now()
                            
                            news_item = {
                                'title': f"[{bid_type}] {title}",
                                'link': detail_url,
                                'pub_date': pub_date,
                                'description': f"项目名称: {title}\n发布时间: {publish_date}\n类型: {bid_type}",
                                'category': bid_type
                            }
                            
                            all_items.append(news_item)
                            
                        except Exception as e:
                            print(f"处理单条{bid_type}信息时出错: {e}")
                            continue
            
        except Exception as e:
            print(f"抓取{bid_type}时出错: {e}")
            continue
    
    # 如果没有从API获取到数据，尝试从HTML页面抓取
    if not all_items:
        print("API数据为空，尝试从HTML页面抓取...")
        all_items = fetch_from_html()
    
    # 按发布时间排序
    all_items.sort(key=lambda x: x['pub_date'], reverse=True)
    return all_items[:30]  # 返回最新的30条

def fetch_from_html():
    """从HTML页面抓取招标信息（备用方案）"""
    base_url = "https://www.whzbtbxt.cn"
    all_items = []
    
    try:
        # 直接访问首页获取招标信息
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(base_url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找招标公告区域
        tender_section = soup.find('div', {'id': 'tenderNotice'})
        if tender_section:
            # 查找招标公告列表
            tender_items = tender_section.find_all('li', class_='tLi')
            
            for item in tender_items[:15]:  # 取前15条
                try:
                    title_elem = item.find('a', class_='project')
                    time_elem = item.find('span', class_='time')
                    
                    if title_elem and time_elem:
                        title = title_elem.get_text().strip()
                        detail_url = title_elem.get('href', '')
                        publish_time = time_elem.get_text().strip()
                        
                        # 处理URL
                        if detail_url and not detail_url.startswith('http'):
                            if detail_url.startswith('/'):
                                detail_url = base_url + detail_url
                            else:
                                detail_url = base_url + '/#' + detail_url
                        
                        # 处理发布时间
                        pub_date = datetime.datetime.now()
                        if publish_time:
                            try:
                                pub_date = datetime.datetime.strptime(publish_time, '%Y-%m-%d')
                            except:
                                pub_date = datetime.datetime.now()
                        
                        news_item = {
                            'title': f"[招标公告] {title}",
                            'link': detail_url,
                            'pub_date': pub_date,
                            'description': f"项目名称: {title}\n发布时间: {publish_time}",
                            'category': '招标公告'
                        }
                        
                        all_items.append(news_item)
                        
                except Exception as e:
                    print(f"处理HTML招标项目时出错: {e}")
                    continue
                    
    except Exception as e:
        print(f"从HTML页面抓取时出错: {e}")
    
    return all_items

def generate_rss_feed(news_items):
    """生成RSS文件"""
    fg = FeedGenerator()
    fg.title('武汉公共资源交易平台 - 招标信息')
    fg.link(href='https://www.whzbtbxt.cn', rel='alternate')
    fg.description('自动抓取武汉公共资源交易平台的招标公告、变更公告、中标结果等信息')
    fg.language('zh-cn')
    for news in news_items:
        fe = fg.entry()
        fe.title(news['title'])
        fe.link(href=news['link'])
        fe.published(news['pub_date'])
        fe.description(news['description'])
        fe.category(term=news['category'])
    fg.rss_file('rss.xml', pretty=True)
    print("RSS文件生成成功！")

    def main():
        print("开始抓取武汉公共资源交易平台招标信息...")
        try:
            news_items = fetch_bidding_info()
            if news_items:
                print(f"成功抓取到 {len(news_items)} 条招标信息")
                generate_rss_feed(news_items)
           else:
                print("未抓取到任何招标信息")
                # 创建一个空的RSS文件以避免错误
                fg = FeedGenerator()
                fg.title('武汉公共资源交易平台 - 招标信息')
                fg.link(href='https://www.whzbtbxt.cn')
                fg.description('暂无最新招标信息')
                fg.rss_file('rss.xml') 
            
        except Exception as e:
            print(f"程序执行出错: {e}")
            # 确保总是生成一个RSS文件，即使出错
            fg = FeedGenerator()
            fg.title('武汉公共资源交易平台 - 招标信息')
            fg.link(href='https://www.whzbtbxt.cn')
            fg.description('数据抓取暂时出现问题')
            fg.rss_file('rss.xml')
 
  if __name__ == '__main__':




