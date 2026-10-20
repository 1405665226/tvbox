var rule = {
    title: 'Jable TV',
    host: 'https://jable.tv',
    searchable: 1,
    quickSearch: 0,
    headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15',
        'Cookie': 'language=cn_CN'
    },
    // 动态获取首页分类及热门/最新标签
    home: function() {
        let url = this.host + '/categories/?mode=async&function=get_block&block_id=list_categories_video_categories_list&sort_by=avg_videos_popularity';
        let html = request(url, {headers: this.headers});
        let $ = cheerio.load(html);
        let classes = [
            {type_id: 'latest-updates', type_name: '💡 最新更新'},
            {type_id: 'hot', type_name: '🔥 熱門排行'},
            {type_id: 'new-release', type_name: '🆕 新作上映'}
        ];
        if (!global.jableCatMap) global.jableCatMap = {};
        $('.container .col-6.col-sm-4.col-lg-3').each((_, e) => {
            let name = $(e).find('h4').text().trim();
            let href = $(e).find('a').attr('href');
            if (name && href && !name.includes('首页')) {
                let id = href.replace(/\/categories\//g, '').replace(/\//g, '');
                classes.push({
                    type_id: id,
                    type_name: name
                });
                global.jableCatMap[id] = href.startsWith('http') ? href : this.host + href;
            }
        });
        return JSON.stringify({class: classes, list: []});
    },
    // 分类/列表及分页数据解析
    category: function(cateId, page, filter, by) {
        let d = [];
        let targetUrl = '';
        if (cateId === 'latest-updates' || cateId === 'hot' || cateId === 'new-release') {
            let baseUrl = this.host + '/' + cateId + '/';
            targetUrl = page == 1 ? baseUrl : baseUrl + page + '/';
        } else {
            let catHref = global.jableCatMap && global.jableCatMap[cateId] ? global.jableCatMap[cateId] : (this.host + '/categories/' + cateId + '/');
            targetUrl = catHref + '?mode=async&function=get_block&block_id=list_videos_common_videos_list&sort_by=post_date&from=' + page + '&_=' + new Date().getTime();
        }
        let html = request(targetUrl, {headers: this.headers});
        let $ = cheerio.load(html);
        let items = $('.video-img-box').length > 0 ? $('.video-img-box') : $('#list_videos_common_videos_list .container .row > div');
        items.each((_, element) => {
            let $el = $(element);
            let aTitle = $el.find('.title a');
            let href = aTitle.attr('href') || $el.find('.img-box a').attr('href');
            let title = aTitle.text().trim();
            let img = $el.find('.img-box img');
            let cover = img.attr('data-src') || img.attr('src');
            let duration = $el.find('.label').text().trim();
            let views = $el.find('.sub-title').text().trim();
            if (href && title) {
                d.push({
                    vod_id: href.startsWith('http') ? href : this.host + href,
                    vod_name: title,
                    vod_pic: cover,
                    vod_remarks: duration || views
                });
            }
        });
        return JSON.stringify({list: d});
    },
    // 详情页与直链解析
    detail: function(id) {
        let html = request(id, {headers: this.headers});
        let playUrl = '';
        let hlsMatch = html.match(/var\s+hlsUrl\s*=\s*['"]([^'"]+)['"]/i) || html.match(/hlsUrl\s*=\s*['"]([^'"]+)['"]/i);
        if (hlsMatch) {
            playUrl = hlsMatch[1];
        } else {
            let m3u8Match = html.match(/(https?:\/\/[^'"]+\.m3u8[^'"]*)/i);
            if (m3u8Match) playUrl = m3u8Match[1];
        }
        let $ = cheerio.load(html);
        let vod = {
            vod_id: id,
            vod_name: $('title').text().trim() || 'Jable Video',
            vod_play_from: 'Jable直连',
            vod_play_url: '原画 1080P/4K$' + playUrl
        };
        return JSON.stringify({list: [vod]});
    },
    // 播放配置与请求头
    play: function(flag, id, flags) {
        return JSON.stringify({
            parse: 0,
            url: id,
            header: {
                'User-Agent': this.headers['User-Agent'],
                'Referer': this.host + '/'
            }
        });
    },
    // 全局番号/关键词搜索
    search: function(wd, page) {
        let d = [];
        let url = this.host + '/search/' + encodeURIComponent(wd) + '/' + page + '/';
        let html = request(url, {headers: this.headers});
        let $ = cheerio.load(html);
        let items = $('.video-img-box').length > 0 ? $('.video-img-box') : $('#list_videos_videos_list_search_result .container .row > div');
        items.each((_, element) => {
            let $el = $(element);
            let aTitle = $el.find('.title a');
            let href = aTitle.attr('href') || $el.find('.img-box a').attr('href');
            let title = aTitle.text().trim();
            let img = $el.find('.img-box img');
            let cover = img.attr('data-src') || img.attr('src');
            let duration = $el.find('.label').text().trim();
            if (href && title) {
                d.push({
                    vod_id: href.startsWith('http') ? href : this.host + href,
                    vod_name: title,
                    vod_pic: cover,
                    vod_remarks: duration
                });
            }
        });
        return JSON.stringify({list: d});
    }
};
