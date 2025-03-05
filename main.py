import os
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_base_urls():
    # 从本地gdzb.txt提取基础URL
    base_urls = set()
    try:
        with open('gdzb.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            urls = re.findall(r'(http://[^/]+/)[^\s]*udp/239\.77\.0\.84:5146', content)
            base_urls.update(urls)
    except FileNotFoundError:
        print("本地gdzb.txt未找到，跳过本地提取")

    # 从远程gdcn.txt提取URL
    try:
        response = requests.get(
            'https://d.kstore.dev/download/10694/%E6%97%A7%E6%96%87%E4%BB%B6/%E7%BB%84%E6%92%ADId/gdcn.txt',
            timeout=10
        )
        remote_urls = re.findall(r'(http://[^/\s]+/)', response.text)
        base_urls.update(remote_urls)
    except Exception as e:
        print(f"远程文件获取失败: {str(e)}")

    return list(base_urls)

def speed_test(url):
    # 测速函数（3秒超时，总时6秒）
    test_url = f"{url}udp/239.77.0.84:5146"
    start_time = time.time()
    try:
        with requests.get(test_url, stream=True, timeout=(3, 6)) as response:
            content = b''
            for chunk in response.iter_content(chunk_size=1024):
                if time.time() - start_time > 6:
                    raise TimeoutError()
                content += chunk
                if len(content) >= 1024:  # 收到1KB即视为成功
                    return url
    except:
        return None

def process_gdnet(valid_urls):
    # 处理gdNet.txt生成最终内容
    output = []
    try:
        with open('gdNet.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    name, rtp = line.strip().split(',')
                    ip_port = rtp.replace('rtp://', '')
                    for base in valid_urls:
                        new_entry = f"{name},{base}udp/{ip_port}"
                        output.append(new_entry)
    except FileNotFoundError:
        print("gdNet.txt未找到！")
    return output

def main():
    # 第一步：获取所有基础URL
    base_urls = fetch_base_urls()
    print(f"发现基础URL: {base_urls}")

    # 第二步：测速筛选有效URL
    valid_urls = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(speed_test, url): url for url in base_urls}
        for future in as_completed(futures):
            result = future.result()
            if result:
                valid_urls.append(result)
    
    print(f"有效URL: {valid_urls}")

    # 第三步：生成gdNet内容
    final_content = process_gdnet(valid_urls)

    # 第四步：强制覆盖写入gdzb.txt
    with open('gdzb.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_content))

    # GitHub Actions自动提交
    if 'GITHUB_ACTIONS' in os.environ:
        os.system('git config --global user.name "l19270149853"')
        os.system('git config --global user.email "362213335lkh@gmail.com"')
        os.system('git add gdzb.txt')
        os.system('git commit -m "自动更新直播源"')
        os.system('git push origin main')

if __name__ == '__main__':
    main()
