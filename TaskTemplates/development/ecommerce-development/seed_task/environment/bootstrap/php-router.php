<?php

$documentRoot = getenv('WP_ROOT') ?: '/var/www/html';
$uri = urldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/');
$candidate = realpath($documentRoot . $uri);

if ($uri !== '/' && $candidate && str_starts_with($candidate, realpath($documentRoot)) && is_file($candidate)) {
    return false;
}

require $documentRoot . '/index.php';
