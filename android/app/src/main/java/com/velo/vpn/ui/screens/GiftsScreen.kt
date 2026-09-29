package com.velo.vpn.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.components.*

@Composable fun GiftsScreen(nav: NavHostController, accountVm: AccountViewModel) {
    val account by accountVm.state.collectAsState()
    Scaffold(bottomBar = { VeloBottomBar(nav, Routes.Gifts) }) { pad ->
        Column(Modifier.fillMaxSize().padding(pad).padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            VeloHeader(hearts = account.hearts)
            Text("هدایا", fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)
            Text("با فعالیت‌ها قلب جمع کنید و از امکانات بیشتر لذت ببرید.", color = MaterialTheme.colorScheme.onSurface.copy(alpha=.55f))
            Spacer(Modifier.height(4.dp))
            FeatureRow(Icons.Default.FactCheck, "ماموریت‌ها", "با کارهای ساده قلب بگیرید") { nav.navigate(Routes.Missions) }
            FeatureRow(Icons.Default.GroupAdd, "دعوت دوستان", "دوستانتان را دعوت کنید و قلب بگیرید") { nav.navigate(Routes.Referral) }
            FeatureRow(Icons.Default.Favorite, "حمایت از پروژه", "با حمایت از Velo در توسعه آن همراه باشید") { nav.navigate(Routes.Support) }
            FeatureRow(Icons.Default.ShoppingBag, "فروشگاه قلب‌ها", "VIP، افزایش سرعت و امکانات ظاهری") { nav.navigate(Routes.Store) }
        }
    }
}
