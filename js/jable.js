// Jable TV - TVBox 专属 JS 爬虫扩展
// 支持: 💡最新更新 / 🔥热门排行 / 🆕新作上市 / 📚主题分类 / 🔍全局番号搜索 / HLS直链直连播放

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15';

async function home(filter) {
    let classes = [
        { type_id: 'latest-updates', type_name: '💡 最新更新' },
        { type_id: 'hot', type_name: '🔥 熱門排行' },
        { type_id: 'new-release', type_name: '🆕 新作上映' }
    ];
    try {
        let classurl = 'https://jable.tv/categories/?mode=async&function=get_block&block_id=list_categories_video_categories_list&sort_by=avg_videos_popularity';
        let res = req(classurl, { headers: { 'User-Agent': UA } });
        let data = typeof res === 'string' ? res : res.data;
        if (data && !data.includes('Just a moment...')) {
            const $= cheerio.load(data);$('.container .col-6.col-sm-4.col-lg-3').each((_, e) => {
                const name = $(e).find('h4').text().trim();
                const href = $(e).find('a').attr('href');
                if (name && href && !name.includes('首页')) {
                    classes.push({ type_id: href, type_name: name });
                }
            });
        }
    } catch (err) {
        print(`[jable] home error: ${err}`);
    }
    return JSON.stringify({
        class: classes,
        filters: {}
    });
}

async function homeVod() {
    return category('latest-updates', 1, {}, {});
}

async function category(tid, pg, filter, extend) {
    let targetUrl = '';
    let page = pg || 1;
    
    if (tid === 'latest-updates' || tid === 'hot' || tid === 'new-release') {
        const baseUrl = `https://jable.tv/${tid}`;
        targetUrl = page === 1 ? `${baseUrl}/` : `${baseUrl}/${page}/`;
    } else {
        const catUrl = tid.startsWith('http') ? tid : `https://jable.tv${tid}`;
        targetUrl = `${catUrl}?mode=async&function=get_block&block_id=list_videos_common_videos_list&sort_by=post_date&from=${page}&_=${Date.now()}`;
    }

    let res = req(targetUrl, {
        headers: {
            'User-Agent': UA,
            'Cookie': 'language=cn_CN'
        }
    });
    let data = typeof res === 'string' ? res : res.data;

    let cards = [];
    if (data && !data.includes('Just a moment...')) {
        const $ = cheerio.load(data);
        const items = $('.video-img-box').length > 0 
            ? $('.video-img-box') 
            : $('#list_videos_common_videos_list .container .row > div');

        items.each((_, element) => {
            const $el =$(element);
            const aTitle = $el.find('.title a');
            const href = aTitle.attr('href') || $el.find('.img-box a').attr('href');
            const title = aTitle.text().trim();
            const img = $el.find('.img-box img');
            const cover = img.attr('data-src') || img.attr('src');
            const duration = $el.find('.label').text().trim();
            const views = $el.find('.sub-title').text().trim();

            if (href && title) {
                cards.push({
                    vod_id: href.startsWith('http') ? href : `https://jable.tv${href}`,
                    vod_name: title,
                    vod_pic: cover,
                    vod_remarks: duration || views
                });
            }
        });
    }

    return JSON.stringify({
        list: cards,
        page: page,
        pagecount: 999,
        limit: 24,
        total: 9999
    });
}

async function detail(id) {
    const url = id.startsWith('http') ? id : `https://jable.tv${id}`;
    let res = req(url, {
        headers: { 'User-Agent': UA }
    });
    let data = typeof res === 'string' ? res : res.data;

    let playUrl = '';
    if (data && !data.includes('Just a moment...')) {
        const hlsMatch = data.match(/var\s+hlsUrl\s*=\s*['"]([^'"]+)['"]/i) || data.match(/hlsUrl\s*=\s*['"]([^'"]+)['"]/i);
        if (hlsMatch) {
            playUrl = hlsMatch[1];
        } else {
            const m3u8Match = data.match(/(https?:\/\/[^'"]+\.m3u8[^'"]*)/i);
            if (m3u8Match) {
                playUrl = m3u8Match[1];
            }
        }
    }

    let vod = {
        vod_id: id,
        vod_name: 'Jable视频',
        vod_play_from: 'Jable直连',
        vod_play_url: playUrl ? `原画 1080P/4K$${playUrl}` : ''
    };

    return JSON.stringify({
        list: [vod]
    });
}

async function play(flag, id, flags) {
    return JSON.stringify({
        parse: 0,
        url: id,
        header: {
            'User-Agent': UA,
            'Referer': 'https://jable.tv/'
        }
    });
}

async function search(wd, quick, pg) {
    let text = encodeURIComponent(wd);
    let page = pg || 1;
    let url = `https://jable.tv/search/${text}/${page}/`;

    let res = req(url, {
        headers: { 'User-Agent': UA }
    });
    let data = typeof res === 'string' ? res : res.data;

    let cards = [];
    if (data && !data.includes('Just a moment...')) {
        const $ = cheerio.load(data);
        const items = $('.video-img-box').length > 0 
            ? $('.video-img-box') 
            : $('#list_videos_videos_list_search_result .container .row > div');

        items.each((_, element) => {
            const $el =$(element);
            const aTitle = $el.find('.title a');
            const href = aTitle.attr('href') || $el.find('.img-box a').attr('href');
            const title = aTitle.text().trim();
            const img = $el.find('.img-box img');
            const cover = img.attr('data-src') || img.attr('src');
            const duration = $el.find('.label').text().trim();

            if (href && title) {
                cards.push({
                    vod_id: href.startsWith('http') ? href : `https://jable.tv${href}`,
                    vod_name: title,
                    vod_pic: cover,
                    vod_remarks: duration
                });
            }
        });
    }

    return JSON.stringify({
        list: cards,
        page: page,
        pagecount: 999
    });
}
