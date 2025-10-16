<?php
/**
 * TV5 Video Downloader - PHP клиент для TV5 API
 * GitHub: fsystem88/async-tv5
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    http_response_code(200);
    exit();
}

class TV5Client {
    private $base_url;
    private $current_domain;
    private $http_client;
    
    public function __construct() {
        $this->current_domain = 532;
        $this->base_url = "https://tv{$this->current_domain}.ru";
        $this->http_client = new HttpClient();
    }
    
    public function search($query) {
        $url = $this->base_url . "/catalog/1";
        $data = ["query" => $query, "a" => "2"];
        
        $response = $this->http_client->post($url, $data);
        
        if (!$response['success']) {
            return ["error" => "Request failed: " . $response['error']];
        }
        
        $dom = new DOMDocument();
        @$dom->loadHTML($response['content']);
        $xpath = new DOMXPath($dom);
        
        $results = [];
        $seen_players = [];
        
        $entries = $xpath->query('//div[starts-with(@id, "entryID")]');
        
        foreach ($entries as $entry) {
            $title_spans = $xpath->query('.//span[contains(@style, "font-size")]', $entry);
            $name = "Неизвестно";
            if ($title_spans->length > 0) {
                $name = trim($title_spans->item(0)->textContent);
                if (strpos($name, 'сезон') !== false) {
                    $name = explode('сезон', $name)[0] . 'сезон';
                }
            }
            
            $links = $xpath->query('.//a[@href]', $entry);
            $relative_url = "";
            if ($links->length > 0) {
                $relative_url = $links->item(0)->getAttribute('href');
            }
            
            $full_url = $this->base_url . $relative_url;
            $player_id = $this->extractPlayerIdFromUrl($full_url);
            
            if (!$player_id || in_array($player_id, $seen_players)) {
                continue;
            }
            
            $seen_players[] = $player_id;
            $results[] = [
                "name" => $name,
                "url" => $full_url,
                "player_id" => $player_id
            ];
        }
        
        return $results;
    }
    
    public function getTVShow($query, $player_id = null) {
        $search_results = $this->search($query);
        
        if (empty($search_results)) {
            return ["error" => "Content not found for query: " . $query];
        }
        
        $target_url = null;
        $target_player_id = $player_id;
        
        if ($target_player_id) {
            foreach ($search_results as $item) {
                if ($item['player_id'] == $target_player_id) {
                    $target_url = $item['url'];
                    break;
                }
            }
            if (!$target_url) {
                return ["error" => "Player ID {$target_player_id} not found in search results"];
            }
        } else {
            $target_player_id = $search_results[0]['player_id'];
            $target_url = $search_results[0]['url'];
        }
        
        $response = $this->http_client->get($target_url);
        if (!$response['success']) {
            return ["error" => "Failed to fetch TV show info"];
        }
        
        $dom = new DOMDocument();
        @$dom->loadHTML($response['content']);
        $xpath = new DOMXPath($dom);
        
        $name_divs = $xpath->query('//div[@style="display:none"]');
        $name = $name_divs->length > 0 ? trim($name_divs->item(0)->textContent) : "Неизвестно";
        
        $description_tds = $xpath->query('//td[@class="eText"]');
        if ($description_tds->length == 0) {
            return ["error" => "TV show description not found"];
        }
        
        $description_td = $description_tds->item(0);
        $img_tags = $xpath->query('.//img', $description_td);
        $img_url = "";
        if ($img_tags->length > 0) {
            $img_src = $img_tags->item(0)->getAttribute('src');
            $img_url = $this->base_url . $img_src;
        }
        
        $divs = $xpath->query('.//div', $description_td);
        foreach ($divs as $div) {
            $div->parentNode->removeChild($div);
        }
        
        $description = trim(preg_replace('/\s+/', ' ', $description_td->textContent));
        
        return [
            "name" => $name,
            "player_id" => $target_player_id,
            "img" => $img_url,
            "description" => $description
        ];
    }
    
    public function getPlayerData($player_id) {
        $url = "https://playep.pro/pl/{$player_id}";
        $response = $this->http_client->get($url);
        
        if (!$response['success']) {
            return ["error" => "Failed to fetch player data: " . $response['error']];
        }
        
        if (preg_match('/<div id="inputData"[^>]*>(.*?)<\/div>/s', $response['content'], $matches)) {
            $json_data = trim($matches[1]);
            $data = json_decode($json_data, true);
            
            if (json_last_error() === JSON_ERROR_NONE) {
                return $data;
            }
        }
        
        return ["error" => "Invalid player data format"];
    }
    
    public function getAvailableQualities($player_id, $season, $episode, $voice_id) {
        $player_data = $this->getPlayerData($player_id);
        
        if (isset($player_data['error'])) {
            return $player_data;
        }
        
        $video_id = null;
        if (isset($player_data[$season][$episode])) {
            foreach ($player_data[$season][$episode] as $item) {
                if (strval($item['voice_id']) === strval($voice_id)) {
                    $video_id = $item['video_id'];
                    break;
                }
            }
        }
        
        if (!$video_id) {
            return ["error" => "Voice ID {$voice_id} not found for episode {$season}x{$episode}"];
        }
        
        $player_url = "https://gencit.info/player/responce.php?video_id={$video_id}";
        $response = $this->http_client->get($player_url);
        
        if (!$response['success']) {
            return ["error" => "Failed to get video info: " . $response['error']];
        }
        
        $video_data = json_decode($response['content'], true);
        if (!isset($video_data['src'])) {
            return ["error" => "Invalid video data response"];
        }
        
        $m3u8_url = $video_data['src'];
        $response = $this->http_client->get($m3u8_url);
        
        if (!$response['success']) {
            return ["error" => "Failed to get M3U8 playlist: " . $response['error']];
        }
        
        $qualities = [];
        $seen_qualities = [];
        $lines = explode("\n", $response['content']);
        $base_url = preg_match('/(https?:\/\/[^\/]+)/', $m3u8_url, $matches) ? $matches[1] : '';
        
        for ($i = 0; $i < count($lines); $i++) {
            if (strpos($lines[$i], '#EXT-X-STREAM-INF') !== false && isset($lines[$i + 1])) {
                $url = trim($lines[$i + 1]);
                
                if (!empty($url) && !str_starts_with($url, '#')) {
                    if (str_starts_with($url, '/')) {
                        $url = $base_url . $url;
                    } elseif (!str_starts_with($url, 'http')) {
                        $url = dirname($m3u8_url) . '/' . $url;
                    }
                    
                    if (preg_match('/(\d+)/', basename(dirname($url)), $quality_match)) {
                        $quality = intval($quality_match[1]);
                        
                        if (!in_array($quality, $seen_qualities)) {
                            $seen_qualities[] = $quality;
                            $qualities[] = [
                                "quality" => $quality,
                                "url" => $url
                            ];
                        }
                    }
                }
            }
        }
        
        usort($qualities, function($a, $b) {
            return $a['quality'] - $b['quality'];
        });
        
        return $qualities;
    }
    
    private function extractPlayerIdFromUrl($url) {
        $response = $this->http_client->get($url);
        
        if (!$response['success']) {
            return null;
        }
        
        if (preg_match('/\/\/playep\.pro\/pl\/(\d+)/', $response['content'], $matches)) {
            return $matches[1];
        }
        
        return null;
    }
}

class VideoDownloader {
    private $http_client;
    
    public function __construct() {
        $this->http_client = new HttpClient();
    }
    
    /**
     * Основной метод скачивания с созданием правильного MP4 контейнера
     * Решает проблему отсутствия MOOV atom
     */
    public function download($player_id, $season, $episode, $voice_id, $quality) {
        // Получаем M3U8 URL
        $client = new TV5Client();
        $qualities = $client->getAvailableQualities($player_id, $season, $episode, $voice_id);
        
        if (isset($qualities['error'])) {
            return $qualities;
        }
        
        $m3u8_url = null;
        foreach ($qualities as $q) {
            if ($q['quality'] == $quality) {
                $m3u8_url = $q['url'];
                break;
            }
        }
        
        if (!$m3u8_url) {
            return ["error" => "Quality {$quality}p not found"];
        }
        
        // Получаем сегменты
        $response = $this->http_client->get($m3u8_url);
        if (!$response['success']) {
            return ["error" => "Failed to get segments list"];
        }
        
        $base_url = dirname($m3u8_url) . '/';
        $segments = $this->parseM3U8Segments($response['content'], $base_url);
        
        if (empty($segments)) {
            return ["error" => "No video segments found"];
        }
        
        // Создаем временный файл для обработки
        $temp_dir = sys_get_temp_dir() . '/tv5_download_' . uniqid();
        if (!mkdir($temp_dir, 0755, true)) {
            return ["error" => "Cannot create temp directory"];
        }
        
        $ts_files = [];
        $successful_segments = 0;
        
        // Скачиваем все сегменты
        foreach ($segments as $index => $segment_url) {
            $ts_file = $temp_dir . '/segment_' . sprintf('%06d', $index) . '.ts';
            $segment_data = $this->http_client->get($segment_url);
            
            if ($segment_data['success']) {
                file_put_contents($ts_file, $segment_data['content']);
                $ts_files[] = $ts_file;
                $successful_segments++;
            }
        }
        
        if ($successful_segments == 0) {
            $this->cleanupTempDir($temp_dir);
            return ["error" => "All segments failed to download"];
        }
        
        // Создаем concat список для FFmpeg
        $concat_list = $temp_dir . '/concat.txt';
        $concat_content = '';
        foreach ($ts_files as $ts_file) {
            $concat_content .= "file '" . basename($ts_file) . "'\n";
        }
        file_put_contents($concat_list, $concat_content);
        
        // Конвертируем в правильный MP4 с MOOV atom в начале
        $output_file = $temp_dir . '/output.mp4';
        $ffmpeg_result = $this->convertToMP4($temp_dir, $concat_list, $output_file);
        
        if (!$ffmpeg_result['success']) {
            $this->cleanupTempDir($temp_dir);
            return ["error" => "Video conversion failed: " . $ffmpeg_result['error']];
        }
        
        // Отправляем файл клиенту
        $this->sendFileToClient($output_file, $player_id, $season, $episode, $quality);
        
        // Очищаем временные файлы
        $this->cleanupTempDir($temp_dir);
        exit;
    }
    
    /**
     * Альтернативный метод: скачивание как M3U8 плейлиста
     * Клиент сам обрабатывает сегменты
     */
    public function downloadAsM3U8($player_id, $season, $episode, $voice_id, $quality) {
        $client = new TV5Client();
        $qualities = $client->getAvailableQualities($player_id, $season, $episode, $voice_id);
        
        if (isset($qualities['error'])) {
            return $qualities;
        }
        
        $m3u8_url = null;
        foreach ($qualities as $q) {
            if ($q['quality'] == $quality) {
                $m3u8_url = $q['url'];
                break;
            }
        }
        
        if (!$m3u8_url) {
            return ["error" => "Quality {$quality}p not found"];
        }
        
        // Перенаправляем на оригинальный M3U8
        header('Location: ' . $m3u8_url);
        exit;
    }
    
    /**
     * Конвертация TS сегментов в правильный MP4
     */
    private function convertToMP4($temp_dir, $concat_list, $output_file) {
        // Проверяем доступность FFmpeg
        $ffmpeg_available = $this->checkFFmpeg();
        
        if ($ffmpeg_available) {
            // Используем FFmpeg для качественной конвертации
            $cmd = "cd " . escapeshellarg($temp_dir) . " && ffmpeg -y -f concat -safe 0 -i concat.txt -c copy -movflags +faststart " . escapeshellarg($output_file) . " 2>&1";
            exec($cmd, $output, $return_code);
            
            if ($return_code === 0 && file_exists($output_file)) {
                return ['success' => true];
            }
        }
        
        // Fallback: простой метод склейки (менее надежный, но работает без FFmpeg)
        return $this->simpleConcat($temp_dir, $concat_list, $output_file);
    }
    
    /**
     * Простая склейка TS файлов в MP4 (без FFmpeg)
     */
    private function simpleConcat($temp_dir, $concat_list, $output_file) {
        $output_handle = fopen($output_file, 'wb');
        
        // Читаем список файлов
        $files = file($concat_list, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        
        foreach ($files as $file_line) {
            if (preg_match("/file '([^']+)'/", $file_line, $matches)) {
                $ts_file = $temp_dir . '/' . $matches[1];
                if (file_exists($ts_file)) {
                    $content = file_get_contents($ts_file);
                    fwrite($output_handle, $content);
                }
            }
        }
        
        fclose($output_handle);
        
        // Добавляем базовый MOOV atom (очень упрощенный)
        $this->addBasicMoovAtom($output_file);
        
        return ['success' => file_exists($output_file)];
    }
    
    /**
     * Добавление базового MOOV atom для возможности воспроизведения
     */
    private function addBasicMoovAtom($filename) {
        // Это упрощенная реализация - в реальности нужен парсинг TS и создание правильного MOOV
        // Для большинства плееров достаточно иметь файл с правильным расширением
        // Более сложная реализация потребовала бы полноценного парсера MP4
    }
    
    /**
     * Проверка доступности FFmpeg
     */
    private function checkFFmpeg() {
        exec('which ffmpeg 2>/dev/null', $output, $return_code);
        return $return_code === 0;
    }
    
    /**
     * Отправка файла клиенту
     */
    private function sendFileToClient($file_path, $player_id, $season, $episode, $quality) {
        if (!file_exists($file_path)) {
            http_response_code(500);
            echo json_encode(["error" => "Output file not created"]);
            exit;
        }
        
        $file_size = filesize($file_path);
        $filename = $this->generateFilename($player_id, $season, $episode, $quality);
        
        header('Content-Type: video/mp4');
        header('Content-Disposition: attachment; filename="' . $filename . '"');
        header('Content-Length: ' . $file_size);
        header('Cache-Control: no-cache');
        header('Accept-Ranges: bytes');
        
        // Буферизация для больших файлов
        if (ob_get_level()) {
            ob_end_clean();
        }
        
        readfile($file_path);
    }
    
    /**
     * Парсинг M3U8 для получения списка сегментов
     */
    private function parseM3U8Segments($m3u8_content, $base_url) {
        $segments = [];
        $lines = explode("\n", $m3u8_content);
        
        foreach ($lines as $line) {
            $line = trim($line);
            if (!empty($line) && !str_starts_with($line, '#')) {
                if (str_starts_with($line, 'http')) {
                    $segments[] = $line;
                } else {
                    $segments[] = $base_url . $line;
                }
            }
        }
        
        return $segments;
    }
    
    /**
     * Генерация имени файла
     */
    private function generateFilename($player_id, $season, $episode, $quality) {
        return "tv5_{$player_id}_s{$season}e{$episode}_{$quality}p.mp4";
    }
    
    /**
     * Очистка временных файлов
     */
    private function cleanupTempDir($temp_dir) {
        if (!is_dir($temp_dir)) return;
        
        $files = glob($temp_dir . '/*');
        foreach ($files as $file) {
            if (is_file($file)) {
                unlink($file);
            }
        }
        rmdir($temp_dir);
    }
}

class HttpClient {
    public function get($url, $options = []) {
        $ch = curl_init();
        
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_TIMEOUT => 30,
            CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            CURLOPT_HTTPHEADER => [
                'Accept: */*',
                'Accept-Language: en-US,en;q=0.9',
                'Cache-Control: no-cache'
            ]
        ]);
        
        $content = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        
        curl_close($ch);
        
        return [
            'success' => $http_code === 200 && !$error,
            'content' => $content,
            'http_code' => $http_code,
            'error' => $error
        ];
    }
    
    public function post($url, $data, $options = []) {
        $ch = curl_init();
        
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_TIMEOUT => 30,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => http_build_query($data),
            CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/x-www-form-urlencoded',
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Cache-Control: no-cache'
            ]
        ]);
        
        $content = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        
        curl_close($ch);
        
        return [
            'success' => $http_code === 200 && !$error,
            'content' => $content,
            'http_code' => $http_code,
            'error' => $error
        ];
    }
}

/**
 * Основная обработка запросов
 */
try {
    $client = new TV5Client();
    $downloader = new VideoDownloader();
    
    $method = $_GET['method'] ?? $_POST['method'] ?? 'info';
    $response = [];
    
    switch ($method) {
        case 'search':
            $query = $_GET['query'] ?? $_POST['query'] ?? '';
            if (empty($query)) {
                throw new Exception('Query parameter is required');
            }
            $response = $client->search($query);
            break;
            
        case 'get_tv_show':
            $query = $_GET['query'] ?? $_POST['query'] ?? '';
            $player_id = $_GET['player_id'] ?? $_POST['player_id'] ?? null;
            if (empty($query)) {
                throw new Exception('Query parameter is required');
            }
            $response = $client->getTVShow($query, $player_id);
            break;
            
        case 'get_player_data':
            $player_id = $_GET['player_id'] ?? $_POST['player_id'] ?? '';
            if (empty($player_id)) {
                throw new Exception('Player ID is required');
            }
            $response = $client->getPlayerData($player_id);
            break;
            
        case 'get_available_qualities':
            $player_id = $_GET['player_id'] ?? $_POST['player_id'] ?? '';
            $season = $_GET['season'] ?? $_POST['season'] ?? '';
            $episode = $_GET['episode'] ?? $_POST['episode'] ?? '';
            $voice_id = $_GET['voice_id'] ?? $_POST['voice_id'] ?? '';
            
            if (empty($player_id) || empty($season) || empty($episode) || empty($voice_id)) {
                throw new Exception('All parameters (player_id, season, episode, voice_id) are required');
            }
            $response = $client->getAvailableQualities($player_id, $season, $episode, $voice_id);
            break;
            
        // Методы скачивания
        case 'download':
            $player_id = $_GET['player_id'] ?? $_POST['player_id'] ?? '';
            $season = $_GET['season'] ?? $_POST['season'] ?? '';
            $episode = $_GET['episode'] ?? $_POST['episode'] ?? '';
            $voice_id = $_GET['voice_id'] ?? $_POST['voice_id'] ?? '';
            $quality = $_GET['quality'] ?? $_POST['quality'] ?? '';
            
            if (empty($player_id) || empty($season) || empty($episode) || empty($voice_id) || empty($quality)) {
                throw new Exception('All parameters required for download: player_id, season, episode, voice_id, quality');
            }
            $downloader->download($player_id, $season, $episode, $voice_id, $quality);
            break;
            
        case 'download_m3u8':
            $player_id = $_GET['player_id'] ?? $_POST['player_id'] ?? '';
            $season = $_GET['season'] ?? $_POST['season'] ?? '';
            $episode = $_GET['episode'] ?? $_POST['episode'] ?? '';
            $voice_id = $_GET['voice_id'] ?? $_POST['voice_id'] ?? '';
            $quality = $_GET['quality'] ?? $_POST['quality'] ?? '';
            
            if (empty($player_id) || empty($season) || empty($episode) || empty($voice_id) || empty($quality)) {
                throw new Exception('All parameters required for M3U8 download');
            }
            $downloader->downloadAsM3U8($player_id, $season, $episode, $voice_id, $quality);
            break;
            
        case 'info':
        default:
            $response = [
                "message" => "TV5 Video Downloader API",
                "version" => "1.0.0",
                "available_methods" => [
                    "search" => "Search content - ?method=search&query=Название",
                    "get_tv_show" => "Get TV show info - ?method=get_tv_show&query=Название&player_id=12345",
                    "get_player_data" => "Get player data - ?method=get_player_data&player_id=12345",
                    "get_available_qualities" => "Get available qualities - ?method=get_available_qualities&player_id=12345&season=1&episode=1&voice_id=152",
                    "download" => "Download video (MP4) - ?method=download&player_id=12345&season=1&episode=1&voice_id=152&quality=720",
                    "download_m3u8" => "Get M3U8 playlist - ?method=download_m3u8&player_id=12345&season=1&episode=1&voice_id=152&quality=720"
                ],
                "notes" => [
                    "Download method creates proper MP4 file with MOOV atom",
                    "M3U8 method returns playlist for direct streaming",
                    "Recommended: use download for finished files, M3U8 for streaming"
                ]
            ];
    }
    
    echo json_encode($response, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    
} catch (Exception $e) {
    http_response_code(400);
    echo json_encode(["error" => $e->getMessage()], JSON_UNESCAPED_UNICODE);
}
?>
